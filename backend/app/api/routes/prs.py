from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.schemas import (
    ErrorResponse,
    PrAvgClosingTimeResponse,
    PrReviewTimeResponse,
    PrSuccessRateResponse,
)
from app.core.db import get_db
from app.core.utils import format_time_delta, format_time_difference
from app.repositories.base import RepositoryError
from app.repositories.prs import (
    fetch_avg_pr_closing_time,
    fetch_pr_review_time,
    fetch_pr_success_rate,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get(
    "/prs/success-rate",
    response_model=PrSuccessRateResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_pr_success_rate(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    db: Session = Depends(get_db),
):
    """
    Calculate the percentage of closed PRs that were successfully merged.
    """
    try:
        success_stats = fetch_pr_success_rate(db, repo_name)
        if success_stats is None:
            raise HTTPException(
                status_code=404,
                detail=f"No PR data found for repository: {repo_name}",
            )

        total_closed_prs, merged_prs, success_rate = success_stats
        return {
            "repository": repo_name,
            "total_closed_prs": total_closed_prs,
            "merged_prs": merged_prs,
            "success_rate_percent": success_rate,
        }
    except HTTPException:
        raise
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating PR success rate: {str(e)}",
        )


@router.get(
    "/prs/avg-closing-time",
    response_model=PrAvgClosingTimeResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_pr_avg_closing_time(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    start_date: str = Query("2010-01-01", description="Start date in format 'YYYY-MM-DD'"),
    db: Session = Depends(get_db),
):
    """
    Calculate average time between PR opening and closing (either merged or closed without merging).
    """
    try:
        avg_seconds = fetch_avg_pr_closing_time(db, repo_name, start_date)
        if avg_seconds is None:
            raise HTTPException(
                status_code=404,
                detail=f"No PR closing data found for repository: {repo_name}",
            )

        avg_timedelta = timedelta(seconds=avg_seconds)
        return {
            "repository": repo_name,
            "average_closing_time_seconds": avg_seconds,
            "average_closing_time_readable": format_time_delta(avg_timedelta),
        }
    except HTTPException:
        raise
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating PR average closing time: {str(e)}",
        )


@router.get(
    "/prs/review-time",
    response_model=PrReviewTimeResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_pr_review_time(
    repo_name: str = Query(..., description="Repository name in format 'owner/repo'"),
    db: Session = Depends(get_db),
):
    """
    Calculate the average time until the first review for Pull Requests.
    """
    try:
        avg_seconds, reviewed_count = fetch_pr_review_time(db, repo_name)
        readable_time = (
            format_time_difference(avg_seconds) if avg_seconds is not None else None
        )

        return PrReviewTimeResponse(
            repository=repo_name,
            reviewed_pr_count=reviewed_count,
            average_review_time_seconds=avg_seconds,
            average_review_time_readable=readable_time,
        )
    except RepositoryError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating PR review time: {str(e)}",
        )

