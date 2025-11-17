from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.repositories.base import RepositoryError
from app.repositories.issues import fetch_average_resolution_time


def fetch_data_quality_metrics(
    session: Session,
    repo_name: str,
) -> Optional[Tuple]:
    """Return latest event timestamp and seconds since."""
    query = text(
        """
        SELECT 
            MAX(created_at) as latest_event_time,
            NOW() - MAX(created_at) as time_since_latest_event
        FROM github_events
        WHERE repo_name = :repo_name
        """
    )

    try:
        result = session.execute(query, {"repo_name": repo_name})
        row = result.fetchone()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to retrieve data quality metrics") from exc

    if not row or row[0] is None:
        return None
    return row


def fetch_bug_resolution_metrics(
    session: Session,
    repo_name: str,
    start_date: str,
    end_date: str,
) -> Tuple[Optional[float], Optional[int]]:
    """Return average bug resolution seconds and total bug count."""
    try:
        return fetch_average_resolution_time(
            session,
            repo_name,
            start_date,
            end_date,
            label_filters=["bug"],
        )
    except RepositoryError:
        raise
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to calculate bug resolution metrics") from exc


def fetch_release_frequency(
    session: Session,
    repo_name: str,
    start_date: str,
    end_date: str,
) -> List[Tuple[str, int]]:
    """Return release counts per month string."""
    query = text(
        """
        WITH release_events AS (
            SELECT 
                toStartOfMonth(created_at) as month,
                count() as releases
            FROM github_events
            WHERE event_type = 'ReleaseEvent'
              AND repo_name = :repo_name
              AND created_at BETWEEN :start_date AND :end_date
            GROUP BY month
            ORDER BY month
        )
        SELECT 
            formatDateTime(month, '%Y-%m') as month_str,
            releases
        FROM release_events
        """
    )

    try:
        result = session.execute(
            query,
            {"repo_name": repo_name, "start_date": start_date, "end_date": end_date},
        )
        return result.fetchall()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to fetch release frequency data") from exc


def fetch_new_contributors(
    session: Session,
    repo_name: str,
    months: int,
):
    """Return rows containing username, first contribution, and profile url."""
    query = text(
        """
        WITH first_contributions AS (
            SELECT
                actor_login as username,
                min(created_at) as first_contribution_date
            FROM github_events
            WHERE repo_name = :repo_name
              AND event_type IN ('PushEvent', 'PullRequestEvent')
            GROUP BY actor_login
            HAVING first_contribution_date >= subtractMonths(now(), :months)
        )
        SELECT
            username,
            first_contribution_date,
            concat('https://github.com/', username) as profile_url
        FROM first_contributions
        ORDER BY first_contribution_date DESC
        """
    )

    try:
        result = session.execute(
            query,
            {"repo_name": repo_name, "months": months},
        )
        return result.fetchall()
    except SQLAlchemyError as exc:
        raise RepositoryError("Failed to fetch new contributor data") from exc
