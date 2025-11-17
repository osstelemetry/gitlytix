from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.schemas import BugResolutionTimeResponse, DataQualityResponse, ErrorResponse
from app.core.db import get_db
from app.core.utils import format_time_delta, format_time_difference, default_start_date
from app.repositories.base import RepositoryError
from app.repositories.stats import (
    fetch_bug_resolution_metrics,
    fetch_data_quality_metrics,
    fetch_new_contributors,
    fetch_release_frequency,
)

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/")
def read_stats():
    return {"message": "Hello, World!"}

@router.get(
    "/data-quality",
    response_model=DataQualityResponse,
    responses={500: {"model": ErrorResponse}}
)
def get_data_quality(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    db: Session = Depends(get_db)
):
    """
    Get data quality metrics for a repository.
    
    This endpoint provides information about the freshness of data for a specific repository,
    including when the most recent event was recorded and how long ago that was.
    
    This helps users understand how up-to-date the metrics for a repository are.
    """
    try:
        metrics = fetch_data_quality_metrics(db, repo_name)
        if metrics is None:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for repository: {repo_name}"
            )
        latest_event_time, seconds_since_latest = metrics
        
        # Convert seconds to a readable format
        time_since_latest = format_time_difference(seconds_since_latest)
        
        # Determine data freshness status
        data_freshness_status = "Fresh"
        if seconds_since_latest > 86400 * 7:  # More than 7 days
            data_freshness_status = "Outdated"
        elif seconds_since_latest > 86400:  # More than 1 day
            data_freshness_status = "Stale"
            
        return {
            "repository": repo_name,
            "latest_event_time": latest_event_time,
            "time_since_latest_event": time_since_latest,
            "data_freshness_status": data_freshness_status
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
            detail=f"Error retrieving data quality information: {str(e)}"
        )

@router.get(
    "/bugs/avg-resolution-time",
    response_model=BugResolutionTimeResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
def get_bug_avg_resolution_time(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    start_date: str | None = Query(None, description="Start date in format 'YYYY-MM-DD'"),
    end_date: str = Query(None, description="End date in format 'YYYY-MM-DD' (defaults to now)"),
    db: Session = Depends(get_db)
):
    """
    Calculate average time between bug issue opening and closing.
    
    A bug is identified as an issue with a 'bug' label that was closed.
    
    Returns:
    - repository: Repository name
    - period: Time window analyzed
    - average_resolution_time_seconds: Average in seconds
    - average_resolution_time_readable: Human-readable average (e.g., "2 days 3 hours")
    - total_bugs_resolved: Total number of bugs resolved in the time window
    """
    try:
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.utcnow()
        end_date_value = end_dt.strftime("%Y-%m-%d")
        start_date_value = start_date or default_start_date(end=end_dt)
        
        avg_seconds, total_bugs = fetch_bug_resolution_metrics(
            db,
            repo_name,
            start_date_value,
            end_date_value,
        )

        if avg_seconds is None:
            raise HTTPException(
                status_code=404,
                detail=f"No bug resolution data found for repository: {repo_name}"
            )

        avg_timedelta = timedelta(seconds=avg_seconds)
        
        return {
            "repository": repo_name,
            "period": {
                "start": start_date_value,
                "end": end_date_value
            },
            "average_resolution_time_seconds": avg_seconds,
            "average_resolution_time_readable": format_time_delta(avg_timedelta),
            "total_bugs_resolved": total_bugs or 0
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
            detail=f"Error calculating bug resolution time: {str(e)}"
        )

@router.get(
    "/releases/frequency",
    responses={500: {"model": ErrorResponse}}
)
def get_release_frequency(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    start_month: str = Query(None, description="Start month in format 'YYYY-MM' (defaults to 12 months ago)"),
    end_month: str = Query(None, description="End month in format 'YYYY-MM' (defaults to current month)"),
    db: Session = Depends(get_db)
):
    """
    Get release frequency statistics by month.
    
    Returns a list of months with release counts in the format:
    [
        {"month": "2025-01", "releases": 4},
        {"month": "2025-02", "releases": 3},
        ...
    ]
    
    If no months are provided, defaults to last 12 months.
    Returns empty array when there are no releases in range.
    """
    try:
        # Set default date range (last 12 months if no dates provided)
        now = datetime.utcnow()
        current_month = now.strftime("%Y-%m")
        
        if not end_month:
            end_month = current_month
        if not start_month:
            # Calculate approximately 6 months before end_month
            end_date_obj = datetime.strptime(end_month + "-01", "%Y-%m-%d")
            start_date = (end_date_obj - timedelta(days=180)).strftime("%Y-%m")
            start_month = start_date
        else:
            end_date_obj = datetime.strptime(end_month + "-01", "%Y-%m-%d")
        
        # Convert YYYY-MM to first day of month for database query
        start_date = f"{start_month}-01"
        end_date = f"{end_month}-01"
        
        rows = fetch_release_frequency(db, repo_name, start_date, end_date)
        data = [
            {"month": row[0], "releases": row[1]}
            for row in rows
        ]
        return data

    except RepositoryError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving release frequency data: {str(e)}"
        )
    

@router.get(
    "/contributors/new",
    responses={500: {"model": ErrorResponse}}
)
def get_new_contributors(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    months: int = Query(6, description="Time window in months to look for new contributors (default: 6)", ge=1, le=24),
    db: Session = Depends(get_db)
):
    """
    Get list of users who made their first contribution to the repository within the specified time window.
    
    Returns a list of new contributors with their first contribution date and GitHub profile URL.
    Only considers PushEvent and PullRequestEvent as qualifying contributions.
    
    Default time window is 6 months (maximum 24 months allowed).
    """
    try:
        rows = fetch_new_contributors(db, repo_name, months)
        contributors = [
            {
                "username": row[0],
                "first_contribution_date": row[1].strftime("%Y-%m-%d"),
                "profile_url": row[2]
            }
            for row in rows
        ]
        
        return {
            "repository": repo_name,
            "time_window_months": months,
            "new_contributors_count": len(contributors),
            "contributors": contributors
        }

    except RepositoryError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving new contributors data: {str(e)}"
        )
