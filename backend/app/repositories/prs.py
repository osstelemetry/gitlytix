from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.repositories.base import RepositoryError


def fetch_pr_success_rate(
    session: Session,
    repo_name: str,
    start_date: str,
) -> Optional[Tuple[int, int, float]]:
    """Return total closed PRs, merged count, and success percentage."""
    query = text(
        """
        WITH pr_final_states AS (
            SELECT
                number,
                argMax(action, created_at) as final_action,
                argMax(merged, created_at) as final_merged_status,
                max(created_at) as last_updated
            FROM github_events
            WHERE event_type = 'PullRequestEvent'
              AND repo_name = :repo_name
              AND created_at >= :start_date
            GROUP BY number
        )
        SELECT
            COUNT() as total_closed_prs,
            COUNTIf(final_merged_status = 1) as merged_prs,
            ROUND(COUNTIf(final_merged_status = 1) * 100.0 / NULLIF(COUNT(), 0), 2) as success_rate_percent
        FROM pr_final_states
        WHERE final_action = 'closed'
        """
    )

    try:
        result = session.execute(
            query,
            {"repo_name": repo_name, "start_date": start_date},
        )
        row = result.fetchone()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to calculate PR success rate") from exc

    if not row or row[0] is None or row[0] == 0:
        return None

    return int(row[0]), int(row[1]), float(row[2])


def fetch_avg_pr_closing_time(
    session: Session,
    repo_name: str,
    start_date: str,
) -> Optional[float]:
    """Return average seconds between PR open and close."""
    query = text(
        """
        WITH pr_openings AS (
            SELECT 
                repo_name,
                number,
                created_at as opened_at
            FROM github_events
            WHERE event_type = 'PullRequestEvent'
              AND action = 'opened'
              AND repo_name = :repo_name
              AND created_at >= :start_date
        ),
        pr_closings AS (
            SELECT
                repo_name,
                number,
                maxIf(created_at, action = 'closed') as closed_at
            FROM github_events
            WHERE event_type = 'PullRequestEvent'
              AND action = 'closed'
              AND repo_name = :repo_name
              AND created_at >= :start_date
            GROUP BY repo_name, number
        ),
        valid_prs AS (
            SELECT
                o.repo_name,
                o.number,
                o.opened_at,
                c.closed_at
            FROM pr_openings o
            JOIN pr_closings c ON o.repo_name = c.repo_name AND o.number = c.number
            WHERE c.closed_at > o.opened_at
        ),
        closing_times AS (
            SELECT
                repo_name,
                dateDiff('second', opened_at, closed_at) as closing_time_seconds
            FROM valid_prs
        )
        SELECT
            repo_name,
            avg(closing_time_seconds) as avg_seconds
        FROM closing_times
        GROUP BY repo_name
        """
    )

    try:
        result = session.execute(
            query,
            {"repo_name": repo_name, "start_date": start_date},
        )
        row = result.fetchone()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to calculate PR average closing time") from exc

    if not row or row[1] is None:
        return None

    return float(row[1])


def fetch_pr_review_time(
    session: Session,
    repo_name: str,
    start_date: str,
) -> Tuple[Optional[float], int]:
    """Return average seconds to first review and reviewed PR count."""
    query = text(
        """
        WITH pr_opened_times AS (
            SELECT
                number,
                argMin(created_at, created_at) as opened_at,
                argMin(actor_login, created_at) as pr_author
            FROM github_events
            WHERE event_type = 'PullRequestEvent' 
              AND action = 'opened' 
              AND repo_name = :repo_name
              AND created_at >= :start_date
            GROUP BY number
        ),
        review_event_times AS (
            SELECT 
                number, 
                created_at AS review_at, 
                actor_login
            FROM github_events
            WHERE repo_name = :repo_name 
              AND event_type IN ('PullRequestReviewCommentEvent', 'PullRequestReviewEvent')
              AND created_at >= :start_date
        ),
        first_review_times AS (
            SELECT
                rev.number,
                min(rev.review_at) as first_review_at
            FROM review_event_times rev
            JOIN pr_opened_times po ON rev.number = po.number
            WHERE rev.actor_login != po.pr_author AND rev.review_at >= po.opened_at
            GROUP BY rev.number
        )
        SELECT
            avg(dateDiff('second', po.opened_at, fr.first_review_at)) as avg_time_to_first_review_seconds,
            count() as reviewed_pr_count
        FROM pr_opened_times po
        JOIN first_review_times fr ON po.number = fr.number
        """
    )

    try:
        result = session.execute(
            query,
            {"repo_name": repo_name, "start_date": start_date},
        )
        row = result.fetchone()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to calculate PR review time") from exc

    if not row or row[1] is None or row[1] == 0:
        return None, 0

    avg_seconds = float(row[0]) if row[0] is not None else None
    return avg_seconds, int(row[1])
