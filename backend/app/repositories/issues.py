from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.repositories.base import RepositoryError


def fetch_monthly_open_closed_counts(
    session: Session,
    repo_name: str,
    start_date: datetime,
    end_date: datetime,
) -> Sequence[Tuple[datetime, int, int]]:
    """Return monthly opened/closed issue counts for the given window."""
    query = text(
        """
        SELECT
            toStartOfMonth(created_at) AS month,
            countIf(action = 'opened') AS opened,
            countIf(action = 'closed') AS closed
        FROM github_events
        WHERE event_type = 'IssuesEvent'
          AND action IN ('opened', 'closed')
          AND created_at >= :start_date
          AND created_at <= :end_date
          AND repo_name = :repo_name
        GROUP BY month
        ORDER BY month
        """
    )

    try:
        result = session.execute(
            query,
            {"repo_name": repo_name, "start_date": start_date, "end_date": end_date},
        )
        return result.fetchall()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to fetch monthly issue statistics") from exc


def fetch_average_first_response_seconds(
    session: Session,
    repo_name: str,
    start_date: str,
    exclude_opener_comments: bool = True,
) -> Optional[float]:
    """Return the average seconds between issue open and first response comment."""
    query = text(
        """
        WITH issue_openings AS (
            SELECT 
                repo_name,
                number,
                created_at as opened_at,
                actor_login as opener_login
            FROM github_events
            WHERE event_type = 'IssuesEvent'
              AND action = 'opened'
              AND repo_name = :repo_name
              AND created_at >= :start_date
        ),
        first_comments AS (
            SELECT
                io.repo_name,
                io.number,
                io.opened_at,
                MIN(ge.created_at) as first_comment_at
            FROM issue_openings io
            JOIN github_events ge ON io.repo_name = ge.repo_name AND io.number = ge.number
            WHERE ge.event_type = 'IssueCommentEvent'
              AND ge.action = 'created'
              AND ge.created_at > io.opened_at
              AND (:exclude_opener_comments = 0 OR ge.actor_login != io.opener_login)
            GROUP BY io.repo_name, io.number, io.opened_at
        ),
        response_times AS (
            SELECT
                repo_name,
                dateDiff('second', opened_at, first_comment_at) as response_time_seconds
            FROM first_comments
        )
        SELECT
            repo_name,
            avg(response_time_seconds) as avg_seconds
        FROM response_times
        GROUP BY repo_name
        """
    )

    try:
        result = session.execute(
            query,
            {
                "repo_name": repo_name,
                "start_date": start_date,
                "exclude_opener_comments": 1 if exclude_opener_comments else 0,
            },
        )
        row = result.fetchone()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to calculate issue first response time") from exc

    if not row or row[1] is None:
        return None
    return float(row[1])


def fetch_average_resolution_time(
    session: Session,
    repo_name: str,
    start_date: str,
    end_date: str,
    label_filters: Optional[Sequence[str]] = None,
) -> Tuple[Optional[float], Optional[int]]:
    """Return average resolution seconds and total resolved issues for the window."""
    label_condition = ""
    if label_filters:
        label_condition = "              AND hasAny(labels, :label_filters)\n"

    query = text(
        f"""
        WITH issue_events AS (
            SELECT 
                repo_name,
                number,
                action,
                created_at,
                labels
            FROM github_events
            WHERE event_type = 'IssuesEvent'
              AND repo_name = :repo_name
              AND action IN ('opened', 'closed')
              AND created_at BETWEEN :start_date AND :end_date
{label_condition}        ),
        issue_timings AS (
            SELECT
                repo_name,
                number,
                minIf(created_at, action = 'opened') as opened_at,
                maxIf(created_at, action = 'closed') as closed_at,
                countIf(action = 'closed') as closed_events
            FROM issue_events
            GROUP BY repo_name, number
            HAVING opened_at IS NOT NULL
               AND closed_events > 0
        ),
        resolution_times AS (
            SELECT
                repo_name,
                dateDiff('second', opened_at, closed_at) as resolution_time_seconds
            FROM issue_timings
            WHERE closed_at > opened_at
        )
        SELECT
            repo_name,
            avg(resolution_time_seconds) as avg_seconds,
            count() as total_issues
        FROM resolution_times
        GROUP BY repo_name
        """
    )

    params = {"repo_name": repo_name, "start_date": start_date, "end_date": end_date}
    if label_filters:
        params["label_filters"] = list(label_filters)

    try:
        result = session.execute(query, params)
        row = result.fetchone()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to calculate issue resolution time") from exc

    if not row or row[1] is None:
        return None, None

    return float(row[1]), row[2]
