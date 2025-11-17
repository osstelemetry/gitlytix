from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.db import get_db
from app.api.schemas import IssuesOpenClosedMonthlyResponse, ErrorResponse, IssueFirstResponseTimeResponse, IssueAvgResolutionTimeResponse
from app.core.utils import format_time_delta, default_start_date
from app.repositories.base import RepositoryError
from app.repositories.issues import (
    fetch_average_first_response_seconds,
    fetch_average_resolution_time,
    fetch_monthly_open_closed_counts,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get(
    "/issues/open-closed",
    response_model=IssuesOpenClosedMonthlyResponse,
    responses={500: {"model": ErrorResponse}}
)
def get_open_closed_issues(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    db: Session = Depends(get_db)
):
    """
    Get monthly issue statistics for the past 6 months from ClickHouse.
    Returns counts of opened and closed issues formatted with month names.
    """
    try:
        # Calculate date range - last 6 months from now
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # ~6 months
        
        db_results = fetch_monthly_open_closed_counts(db, repo_name, start_date, end_date)
        
        # Process results
        monthly_stats = []
        
        # Generate all months in the period
        current_month = start_date.replace(day=1)
        while current_month <= end_date.replace(day=1):
            # ClickHouse returns dates as datetime.date objects
            current_month_date = current_month.date()
            
            # Find matching data from DB
            db_data = next((row for row in db_results if row[0] == current_month_date), None)
            
            # Format month as YYYY-MM to match MonthlyIssueStat
            month_str = current_month.strftime("%Y-%m")
            
            monthly_stats.append({
                "month": month_str,
                "opened": db_data[1] if db_data else 0,
                "closed": db_data[2] if db_data else 0
            })
            
            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)
        
        # Get only the last 6 months
        last_6_months = monthly_stats[-6:]
        
        return {
            "repository": repo_name,
            "data": last_6_months
        }
        
    except RepositoryError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving monthly issues data: {str(e)}"
        )
    


@router.get(
    "/issues/first-response-time",
    response_model=IssueFirstResponseTimeResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
def get_first_response_time(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    start_date: Optional[str] = Query(None, description="Start date in format 'YYYY-MM-DD'"),
    exclude_opener_comments: bool = Query(True, description="Exclude comments by the issue opener"),
    db: Session = Depends(get_db)
):
    """
    Calculate average time between issue opening and first response comment.
    
    Returns:
    - repository: Repository name
    - average_response_time_seconds: Average in seconds
    - average_response_time_readable: Human-readable average (e.g., "2 hours 30 minutes")
    """
    try:
        start_date_value = start_date or default_start_date()
        avg_seconds = fetch_average_first_response_seconds(
            db,
            repo_name,
            start_date_value,
            exclude_opener_comments,
        )

        if avg_seconds is None:
            raise HTTPException(
                status_code=404,
                detail=f"No response data found for issues in repository: {repo_name}"
            )
        avg_timedelta = timedelta(seconds=avg_seconds)
        
        return {
            "repository": repo_name,
            "average_response_time_seconds": avg_seconds,
            "average_response_time_readable": format_time_delta(avg_timedelta)
        }

    except HTTPException:
        raise
    except RepositoryError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating first response time: {str(e)}"
        )

    
@router.get(
    "/issues/avg-resolution-time",
    response_model=IssueAvgResolutionTimeResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
def get_issue_avg_resolution_time(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    start_date: Optional[str] = Query(None, description="Start date in format 'YYYY-MM-DD'"),
    end_date: str = Query(None, description="End date in format 'YYYY-MM-DD' (defaults to now)"),
    label: Optional[str] = Query(None, description="Optional label to filter issues (e.g., 'bug')"),
    db: Session = Depends(get_db)
):
    """
    Calculate average time between issue opening and closing.
    
    Returns:
    - repository: Repository name
    - period: Time window analyzed
    - average_resolution_time_seconds: Average in seconds
    - average_resolution_time_readable: Human-readable average (e.g., "2 days 3 hours")
    - total_issues_resolved: Total number of issues resolved in the time window
    """
    try:
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.utcnow()
        end_date_value = end_dt.strftime("%Y-%m-%d")
        start_date_value = start_date or default_start_date(end=end_dt)
        
        label_filters = [label] if label else None
        avg_seconds, total_issues = fetch_average_resolution_time(
            db,
            repo_name,
            start_date_value,
            end_date_value,
            label_filters=label_filters,
        )

        if avg_seconds is None:
            raise HTTPException(
                status_code=404,
                detail=f"No issue resolution data found for repository: {repo_name}"
            )
        total_resolved = total_issues or 0
        avg_timedelta = timedelta(seconds=avg_seconds)
        
        return {
            "repository": repo_name,
            "period": {
                "start": start_date_value,
                "end": end_date_value
            },
            "average_resolution_time_seconds": avg_seconds,
            "average_resolution_time_readable": format_time_delta(avg_timedelta),
            "total_issues_resolved": total_resolved
        }

    except HTTPException:
        raise
    except RepositoryError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating issue resolution time: {str(e)}"
        )
