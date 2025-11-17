#!/usr/bin/env python3
"""
Database initialization script for ClickHouse.
Creates the github_events table and populates it with dummy data.
"""

import asyncio
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import List

import clickhouse_connect
from clickhouse_connect.driver import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ClickHouse connection settings
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_HTTP_PORT = int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123"))  # HTTP interface port
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse123")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")

# Sample repositories for dummy data
SAMPLE_REPOS = [
    "facebook/react",
    "microsoft/vscode",
    "google/tensorflow",
    "vercel/next.js"
]

# Sample users
SAMPLE_USERS = [
    "alice_dev", "bob_coder", "charlie_contributor", "diana_maintainer",
    "eve_reviewer", "frank_submitter", "grace_committer", "henry_tester",
    "ivy_designer", "jack_admin"
]

# Sample event types with weights (more common events have higher weights)
EVENT_TYPE_WEIGHTS = {
    'PushEvent': 30,  # Reduced slightly to make room for new events
    'IssuesEvent': 15,
    'PullRequestEvent': 22,  # Reduced slightly
    'IssueCommentEvent': 10,
    'PullRequestReviewCommentEvent': 12,  # Increased for more reviews
    'ReleaseEvent': 3,
    'MemberEvent': 3,  # Added new contributors
    'CreateEvent': 2,
    'DeleteEvent': 1,
    'WatchEvent': 1,
    'ForkEvent': 1
}

def wait_for_clickhouse(client: Client, max_attempts: int = 30) -> bool:
    """Wait for ClickHouse to be ready."""
    for attempt in range(max_attempts):
        try:
            client.ping()
            logger.info("ClickHouse is ready!")
            return True
        except Exception as e:
            logger.info(f"Waiting for ClickHouse... (attempt {attempt + 1}/{max_attempts}): {e}")
            time.sleep(2)
    return False

def create_table_if_not_exists(client: Client) -> None:
    """Create the github_events table if it doesn't exist."""
    
    # Check if table exists
    result = client.query("""
        SELECT name FROM system.tables 
        WHERE database = currentDatabase() AND name = 'github_events'
    """)
    
    if result.result_rows:
        logger.info("Table 'github_events' already exists, skipping creation")
        return
    
    # Define the CREATE TABLE SQL directly to avoid parsing issues
    create_table_sql = """
    CREATE TABLE github_events
    (
        file_time DateTime,
        event_type Enum('CommitCommentEvent' = 1, 'CreateEvent' = 2, 'DeleteEvent' = 3, 'ForkEvent' = 4,
                        'GollumEvent' = 5, 'IssueCommentEvent' = 6, 'IssuesEvent' = 7, 'MemberEvent' = 8,
                        'PublicEvent' = 9, 'PullRequestEvent' = 10, 'PullRequestReviewCommentEvent' = 11,
                        'PullRequestReviewThreadEvent' = 12, 'PushEvent' = 13, 'ReleaseEvent' = 14, 
                        'SponsorshipEvent' = 15, 'WatchEvent' = 16),
        actor_login LowCardinality(String),
        repo_name LowCardinality(String),
        created_at DateTime,
        updated_at DateTime,
        action Enum('none' = 0, 'created' = 1, 'added' = 2, 'edited' = 3, 'deleted' = 4, 'opened' = 5, 'closed' = 6, 'reopened' = 7, 'assigned' = 8, 'unassigned' = 9,
                    'labeled' = 10, 'unlabeled' = 11, 'review_requested' = 12, 'review_request_removed' = 13, 'synchronize' = 14, 'started' = 15, 'published' = 16, 'update' = 17, 'create' = 18, 'fork' = 19, 'merged' = 20,
                    'resolved' = 21, 'unresolved' = 22),
        comment_id UInt64,
        body String,
        path String,
        position Int32,
        line Int32,
        ref LowCardinality(String),
        ref_type Enum('none' = 0, 'branch' = 1, 'tag' = 2, 'repository' = 3, 'unknown' = 4),
        creator_user_login LowCardinality(String),
        number UInt32,
        title String,
        labels Array(LowCardinality(String)),
        state Enum('none' = 0, 'open' = 1, 'closed' = 2),
        locked UInt8,
        assignee LowCardinality(String),
        assignees Array(LowCardinality(String)),
        comments UInt32,
        author_association Enum('NONE' = 0, 'CONTRIBUTOR' = 1, 'OWNER' = 2, 'COLLABORATOR' = 3, 'MEMBER' = 4, 'MANNEQUIN' = 5),
        closed_at DateTime,
        merged_at DateTime,
        merge_commit_sha String,
        requested_reviewers Array(LowCardinality(String)),
        requested_teams Array(LowCardinality(String)),
        merged UInt8,
        mergeable UInt8,
        mergeable_state Enum('unknown' = 0, 'dirty' = 1, 'clean' = 2, 'unstable' = 3, 'draft' = 4, 'blocked' = 5),
        merged_by LowCardinality(String),
        review_comments UInt32,
        maintainer_can_modify UInt8,
        commits UInt32,
        additions UInt32,
        deletions UInt32,
        changed_files UInt32,
        commit_id String,
        original_commit_id String,
        member_login LowCardinality(String),
        release_tag_name String,
        release_name String,
        review_state Enum('none' = 0, 'approved' = 1, 'changes_requested' = 2, 'commented' = 3, 'dismissed' = 4, 'pending' = 5)
    ) ENGINE = MergeTree ORDER BY (event_type, repo_name, created_at)
    """
    
    logger.info("Creating github_events table...")
    client.command(create_table_sql)
    logger.info("Table created successfully!")

def generate_dummy_data(num_events: int = 1000) -> List[tuple]:
    """Generate dummy data for the github_events table."""
    
    events = []
    base_time = datetime.now() - timedelta(days=90)  # Extended to 90 days for more release history
    default_datetime = datetime(1970, 1, 1)  # Default for null datetime fields
    
    # Track PRs and Issues for response events
    pr_events = []
    issue_events = []
    new_contributors = set()  # Track new contributors per repo
    
    # Generate weekly releases first (guaranteed)
    release_events = []
    current_week = base_time
    version_major = 1
    version_minor = 0
    
    while current_week < datetime.now():
        for repo in SAMPLE_REPOS:
            # Create a release every 1-2 weeks per repo
            if random.random() > 0.3:  # 70% chance of release per week per repo
                release_time = current_week + timedelta(days=random.randint(0, 6))
                if release_time < datetime.now():
                    version_patch = random.randint(0, 10)
                    release_tag = f"v{version_major}.{version_minor}.{version_patch}"
                    release_name = f"Release {release_tag}"
                    
                    release_event = (
                        release_time,  # file_time
                        'ReleaseEvent',
                        random.choice(SAMPLE_USERS),  # actor_login
                        repo,  # repo_name
                        release_time,  # created_at
                        release_time,  # updated_at
                        'published',  # action
                        0,  # comment_id
                        f"Release {release_tag} with new features and bug fixes",  # body
                        '',  # path
                        0,  # position
                        0,  # line
                        f'refs/tags/{release_tag}',  # ref
                        'tag',  # ref_type
                        random.choice(SAMPLE_USERS),  # creator_user_login
                        0,  # number
                        release_name,  # title
                        ['release'],  # labels
                        'none',  # state
                        0,  # locked
                        '',  # assignee
                        [],  # assignees
                        0,  # comments
                        'OWNER',  # author_association
                        default_datetime,  # closed_at
                        default_datetime,  # merged_at
                        '',  # merge_commit_sha
                        [],  # requested_reviewers
                        [],  # requested_teams
                        0,  # merged
                        0,  # mergeable
                        'unknown',  # mergeable_state
                        '',  # merged_by
                        0,  # review_comments
                        0,  # maintainer_can_modify
                        0,  # commits
                        0,  # additions
                        0,  # deletions
                        0,  # changed_files
                        f"release_commit_{random.randint(1000000, 9999999)}",  # commit_id
                        '',  # original_commit_id
                        '',  # member_login
                        release_tag,  # release_tag_name
                        release_name,  # release_name
                        'none'  # review_state
                    )
                    release_events.append(release_event)
        
        current_week += timedelta(weeks=1)
        # Increment version occasionally
        if random.random() > 0.8:
            version_minor += 1
        if version_minor > 10:
            version_major += 1
            version_minor = 0
    
    # Add release events to our events list
    events.extend(release_events)
    
    # Generate new contributors (MemberEvent) - 2-3 per repo per month
    member_events = []
    for repo in SAMPLE_REPOS:
        # Generate 3-6 new contributors over 90 days
        num_new_contributors = random.randint(3, 6)
        for _ in range(num_new_contributors):
            contributor_time = base_time + timedelta(
                days=random.randint(0, 90)
            )
            if contributor_time < datetime.now():
                new_contributor = random.choice(SAMPLE_USERS)
                new_contributors.add((repo, new_contributor))
                
                member_event = (
                    contributor_time,  # file_time
                    'MemberEvent',
                    random.choice(SAMPLE_USERS),  # actor_login (who added them)
                    repo,  # repo_name
                    contributor_time,  # created_at
                    contributor_time,  # updated_at
                    'added',  # action
                    0,  # comment_id
                    f"Added {new_contributor} as a collaborator",  # body
                    '',  # path
                    0,  # position
                    0,  # line
                    '',  # ref
                    'none',  # ref_type
                    random.choice(SAMPLE_USERS),  # creator_user_login
                    0,  # number
                    '',  # title
                    [],  # labels
                    'none',  # state
                    0,  # locked
                    '',  # assignee
                    [],  # assignees
                    0,  # comments
                    'OWNER',  # author_association
                    default_datetime,  # closed_at
                    default_datetime,  # merged_at
                    '',  # merge_commit_sha
                    [],  # requested_reviewers
                    [],  # requested_teams
                    0,  # merged
                    0,  # mergeable
                    'unknown',  # mergeable_state
                    '',  # merged_by
                    0,  # review_comments
                    0,  # maintainer_can_modify
                    0,  # commits
                    0,  # additions
                    0,  # deletions
                    0,  # changed_files
                    f"member_commit_{random.randint(1000000, 9999999)}",  # commit_id
                    '',  # original_commit_id
                    new_contributor,  # member_login
                    '',  # release_tag_name
                    '',  # release_name
                    'none'  # review_state
                )
                member_events.append(member_event)
    
    # Add member events to our events list
    events.extend(member_events)
    
    # First, generate PRs and Issues
    pr_issue_events = []
    remaining_events = max(0, num_events - len(release_events) - len(member_events))
    
    # Calculate how many PRs and Issues we want to generate first
    pr_weight = EVENT_TYPE_WEIGHTS['PullRequestEvent']
    issue_weight = EVENT_TYPE_WEIGHTS['IssuesEvent']
    total_weight = sum(EVENT_TYPE_WEIGHTS.values())
    
    num_prs = int((pr_weight / total_weight) * remaining_events)
    num_issues = int((issue_weight / total_weight) * remaining_events)
    
    # Generate PRs first
    for _ in range(num_prs):
        created_at = base_time + timedelta(
            minutes=random.randint(0, 90 * 24 * 60)  # Random time in last 90 days
        )
        repo_name = random.choice(SAMPLE_REPOS)
        actor_login = random.choice(SAMPLE_USERS)
        
        pr_titles = [
            "Fix bug in authentication module",
            "Add new feature for user management",
            "Update documentation for API",
            "Refactor database queries",
            "Improve error handling",
            "Add unit tests for utilities",
            "Optimize performance bottleneck",
            "Security patch for XSS vulnerability"
        ]
        title = random.choice(pr_titles)
        body = f"This PR addresses important changes in the codebase. Includes {random.randint(1, 10)} commits."
        number = random.randint(1, 1000)
        
        ref = random.choice(['main', 'develop', 'feature-branch', 'refs/heads/main', 'refs/heads/feature/new-auth'])
        ref_type = 'branch'
        creator_user_login = actor_login
        
        labels = random.choice([
            ['enhancement'], ['bug'], ['documentation'], 
            ['feature'], ['refactor'], ['performance'],
            ['bug', 'priority-high'], ['enhancement', 'good-first-issue']
        ]) if random.random() > 0.4 else []
        
        locked = 0
        assignee = random.choice(SAMPLE_USERS) if random.random() > 0.7 else ''
        assignees = [random.choice(SAMPLE_USERS)] if random.random() > 0.8 else []
        comments_count = random.randint(0, 20)
        author_association = random.choice(['CONTRIBUTOR', 'OWNER', 'COLLABORATOR', 'MEMBER', 'NONE'])
        merge_commit_sha = f"sha{random.randint(1000000, 9999999)}"
        requested_reviewers = [random.choice(SAMPLE_USERS)] if random.random() > 0.6 else []
        requested_teams = []
        mergeable = random.randint(0, 1)
        mergeable_state = random.choice(['clean', 'dirty', 'unknown', 'unstable'])
        merged_by_candidate = random.choice(SAMPLE_USERS)
        review_comments = random.randint(0, 15)
        maintainer_can_modify = random.randint(0, 1)
        commits = random.randint(1, 8)
        additions = random.randint(10, 500)
        deletions = random.randint(0, 200)
        changed_files = random.randint(1, 12)
        commit_id = f"commit{random.randint(1000000, 9999999)}"
        original_commit_id = f"original{random.randint(1000000, 9999999)}"
        member_login = ''
        release_tag_name = ''
        release_name = ''
        review_state = 'none'
        
        is_closed = random.random() > 0.25
        close_delay_hours = random.randint(4, 240)
        closed_at = created_at + timedelta(hours=close_delay_hours) if is_closed else None
        if closed_at and closed_at > datetime.now():
            closed_at = datetime.now() - timedelta(hours=random.randint(1, 6))
        merged_flag = 1 if closed_at and random.random() > 0.5 else 0
        merged_at = closed_at if merged_flag else default_datetime
        closing_actor = random.choice(SAMPLE_USERS) if closed_at else actor_login
        
        def build_pr_event(event_time, action_value, state_value, closed_value, merged_value, merged_flag_value, actor_value, body_value):
            updated_value = event_time + timedelta(minutes=random.randint(0, 60))
            return (
                event_time,
                'PullRequestEvent',
                actor_value,
                repo_name,
                event_time,
                updated_value,
                action_value,
                0,
                body_value,
                '',
                0,
                0,
                ref,
                ref_type,
                creator_user_login,
                number,
                title,
                labels,
                state_value,
                locked,
                assignee,
                assignees,
                comments_count,
                author_association,
                closed_value,
                merged_value,
                merge_commit_sha if merged_flag_value else '',
                requested_reviewers,
                requested_teams,
                merged_flag_value,
                mergeable,
                mergeable_state,
                merged_by_candidate if merged_flag_value else '',
                review_comments,
                maintainer_can_modify,
                commits,
                additions,
                deletions,
                changed_files,
                commit_id,
                original_commit_id,
                member_login,
                release_tag_name,
                release_name,
                review_state
            )
        
        # Open event
        pr_issue_events.append(
            build_pr_event(
                created_at,
                'opened',
                'open',
                default_datetime,
                default_datetime,
                0,
                actor_login,
                body
            )
        )
        
        if closed_at:
            pr_issue_events.append(
                build_pr_event(
                    closed_at,
                    'closed',
                    'closed',
                    closed_at,
                    merged_at,
                    merged_flag,
                    closing_actor,
                    f"Closing PR #{number}"
                )
            )
        
        # Track this PR for review events
        pr_events.append({
            'repo': repo_name,
            'number': number,
            'created_at': created_at,
            'title': title,
            'author': actor_login,
            'state': 'closed' if closed_at else 'open'
        })
    
    # Generate Issues next
    for _ in range(num_issues):
        created_at = base_time + timedelta(
            minutes=random.randint(0, 90 * 24 * 60)  # Random time in last 90 days
        )
        repo_name = random.choice(SAMPLE_REPOS)
        actor_login = random.choice(SAMPLE_USERS)
        
        issue_titles = [
            "Bug: Application crashes on startup",
            "Feature request: Dark mode support",
            "Documentation: Missing API examples",
            "Bug: Memory leak in data processing",
            "Enhancement: Improve loading performance",
            "Bug: Incorrect validation in forms"
        ]
        title = random.choice(issue_titles)
        body = f"This issue needs attention. Priority: {random.choice(['high', 'medium', 'low'])}"
        number = random.randint(1, 1000)
        
        ref = ''
        ref_type = 'none'
        creator_user_login = actor_login
        
        labels = random.choice([
            ['bug'], ['enhancement'], ['documentation'], 
            ['question'], ['help wanted'], ['good first issue'],
            ['bug', 'priority-critical'], ['enhancement', 'feature-request']
        ]) if random.random() > 0.3 else []
        
        locked = 0
        assignee = random.choice(SAMPLE_USERS) if random.random() > 0.7 else ''
        assignees = [random.choice(SAMPLE_USERS)] if random.random() > 0.8 else []
        comments_count = random.randint(0, 20)
        author_association = random.choice(['CONTRIBUTOR', 'OWNER', 'COLLABORATOR', 'MEMBER', 'NONE'])
        
        is_closed = random.random() > 0.35
        close_delay_hours = random.randint(2, 240)
        closed_at = created_at + timedelta(hours=close_delay_hours) if is_closed else None
        if closed_at and closed_at > datetime.now():
            closed_at = datetime.now() - timedelta(hours=random.randint(1, 6))
        closing_actor = random.choice(SAMPLE_USERS) if closed_at else actor_login
        
        def build_issue_event(event_time, action_value, state_value, closed_value, actor_value, body_value):
            updated_value = event_time + timedelta(minutes=random.randint(0, 60))
            return (
                event_time,
                'IssuesEvent',
                actor_value,
                repo_name,
                event_time,
                updated_value,
                action_value,
                0,
                body_value,
                '',
                0,
                0,
                ref,
                ref_type,
                creator_user_login,
                number,
                title,
                labels,
                state_value,
                locked,
                assignee,
                assignees,
                comments_count,
                author_association,
                closed_value,
                default_datetime,
                '',
                [],
                [],
                0,
                0,
                'unknown',
                '',
                0,
                0,
                0,
                0,
                0,
                0,
                f"commit{random.randint(1000000, 9999999)}",
                f"original{random.randint(1000000, 9999999)}",
                '',
                '',
                '',
                'none'
            )
        
        pr_issue_events.append(
            build_issue_event(
                created_at,
                'opened',
                'open',
                default_datetime,
                actor_login,
                body
            )
        )
        
        if closed_at:
            pr_issue_events.append(
                build_issue_event(
                    closed_at,
                    'closed',
                    'closed',
                    closed_at,
                    closing_actor,
                    f"Closing issue #{number}"
                )
            )
        
        # Track this Issue for comment events
        issue_events.append({
            'repo': repo_name,
            'number': number,
            'created_at': created_at,
            'title': title,
            'author': actor_login,
            'state': 'closed' if closed_at else 'open'
        })
    
    # Add PR and Issue events
    events.extend(pr_issue_events)
    
    # Now generate response events (reviews and comments) with proper timing
    response_events = []
    
    # Generate PR review comments (80% of PRs get reviewed)
    for pr in pr_events:
        if random.random() < 0.8:  # 80% of PRs get reviewed
            # First review comes 30 minutes to 48 hours after PR creation
            review_delay = timedelta(
                minutes=random.randint(30, 48 * 60)  # 30 minutes to 48 hours
            )
            review_time = pr['created_at'] + review_delay
            
            if review_time < datetime.now():
                # Make sure reviewer is different from PR author
                possible_reviewers = [u for u in SAMPLE_USERS if u != pr['author']]
                reviewer = random.choice(possible_reviewers)
                
                review_body = random.choice([
                    "LGTM! Great work on this implementation.",
                    "Could we add some unit tests for this change?",
                    "I think there might be a performance issue in this approach.",
                    "Thanks for the contribution! Just a few minor comments.",
                    "Looks good overall, but please fix the linting errors.",
                    "Great approach! This should resolve the issue effectively.",
                    "Can you please update the documentation as well?",
                    "Nice refactoring! This makes the code much cleaner.",
                    "Consider adding error handling for edge cases.",
                    "The implementation looks solid. Ready to merge!"
                ])
                
                review_event = (
                    review_time,  # file_time
                    'PullRequestReviewCommentEvent',
                    reviewer,  # actor_login
                    pr['repo'],  # repo_name
                    review_time,  # created_at
                    review_time,  # updated_at
                    'created',  # action
                    random.randint(1000000, 9999999),  # comment_id
                    review_body,  # body
                    random.choice(['src/main.py', 'README.md', 'package.json', 'src/components/Auth.js']),  # path
                    random.randint(1, 100),  # position
                    random.randint(1, 1000),  # line
                    'refs/heads/main',  # ref
                    'branch',  # ref_type
                    reviewer,  # creator_user_login
                    pr['number'],  # number
                    '',  # title
                    [],  # labels
                    'none',  # state
                    0,  # locked
                    '',  # assignee
                    [],  # assignees
                    0,  # comments
                    random.choice(['CONTRIBUTOR', 'OWNER', 'COLLABORATOR', 'MEMBER']),  # author_association
                    default_datetime,  # closed_at
                    default_datetime,  # merged_at
                    '',  # merge_commit_sha
                    [],  # requested_reviewers
                    [],  # requested_teams
                    0,  # merged
                    0,  # mergeable
                    'unknown',  # mergeable_state
                    '',  # merged_by
                    0,  # review_comments
                    0,  # maintainer_can_modify
                    0,  # commits
                    0,  # additions
                    0,  # deletions
                    0,  # changed_files
                    f"commit{random.randint(1000000, 9999999)}",  # commit_id
                    f"original{random.randint(1000000, 9999999)}",  # original_commit_id
                    '',  # member_login
                    '',  # release_tag_name
                    '',  # release_name
                    random.choice(['approved', 'changes_requested', 'commented'])  # review_state
                )
                response_events.append(review_event)
    
    # Generate Issue comments (70% of issues get responses)
    for issue in issue_events:
        if random.random() < 0.7:  # 70% of issues get responses
            # First response comes 20 minutes to 24 hours after issue creation
            response_delay = timedelta(
                minutes=random.randint(20, 24 * 60)  # 20 minutes to 24 hours
            )
            response_time = issue['created_at'] + response_delay
            
            if response_time < datetime.now():
                # Make sure responder is different from issue author
                possible_responders = [u for u in SAMPLE_USERS if u != issue['author']]
                responder = random.choice(possible_responders)
                
                response_body = random.choice([
                    "Thanks for reporting this issue!",
                    "I can reproduce this bug. Working on a fix.",
                    "This is a duplicate of issue #123",
                    "Could you provide more details about your environment?",
                    "Fixed in the latest commit.",
                    "This would be a great feature addition!",
                    "We should consider the impact on performance.",
                    "I'll assign this to our next sprint.",
                    "Looking into this now.",
                    "Can you provide steps to reproduce?"
                ])
                
                comment_event = (
                    response_time,  # file_time
                    'IssueCommentEvent',
                    responder,  # actor_login
                    issue['repo'],  # repo_name
                    response_time,  # created_at
                    response_time,  # updated_at
                    'created',  # action
                    random.randint(1000000, 9999999),  # comment_id
                    response_body,  # body
                    '',  # path
                    0,  # position
                    0,  # line
                    '',  # ref
                    'none',  # ref_type
                    responder,  # creator_user_login
                    issue['number'],  # number
                    '',  # title
                    [],  # labels
                    'none',  # state
                    0,  # locked
                    '',  # assignee
                    [],  # assignees
                    0,  # comments
                    random.choice(['CONTRIBUTOR', 'OWNER', 'COLLABORATOR', 'MEMBER']),  # author_association
                    default_datetime,  # closed_at
                    default_datetime,  # merged_at
                    '',  # merge_commit_sha
                    [],  # requested_reviewers
                    [],  # requested_teams
                    0,  # merged
                    0,  # mergeable
                    'unknown',  # mergeable_state
                    '',  # merged_by
                    0,  # review_comments
                    0,  # maintainer_can_modify
                    0,  # commits
                    0,  # additions
                    0,  # deletions
                    0,  # changed_files
                    f"commit{random.randint(1000000, 9999999)}",  # commit_id
                    f"original{random.randint(1000000, 9999999)}",  # original_commit_id
                    '',  # member_login
                    '',  # release_tag_name
                    '',  # release_name
                    'none'  # review_state
                )
                response_events.append(comment_event)
    
    # Add response events
    events.extend(response_events)
    
    # Generate remaining other events to fill up to num_events
    remaining_count = max(0, num_events - len(events))
    other_event_types = ['PushEvent', 'CreateEvent', 'DeleteEvent', 'WatchEvent', 'ForkEvent']
    
    for i in range(remaining_count):
        event_type = random.choice(other_event_types)
        
        created_at = base_time + timedelta(
            minutes=random.randint(0, 90 * 24 * 60)
        )
        updated_at = created_at + timedelta(minutes=random.randint(0, 60))
        
        repo_name = random.choice(SAMPLE_REPOS)
        actor_login = random.choice(SAMPLE_USERS)
        
        if event_type == 'PushEvent':
            action = 'none'
            title = ''
            body = f"Pushed {random.randint(1, 5)} commits"
            number = 0
            state = 'none'
            comment_id = 0
            path = random.choice(['src/main.py', 'src/utils.py', 'README.md'])
            position = 0
            line = 0
        else:
            action = random.choice(['created', 'deleted']) if event_type in ['CreateEvent', 'DeleteEvent'] else 'none'
            title = ''
            body = ''
            number = 0
            state = 'none'
            comment_id = 0
            path = ''
            position = 0
            line = 0
        
        ref = random.choice(['main', 'develop', 'feature-branch'])
        ref_type = 'branch' if ref else 'none'
        
        other_event = (
            created_at,  # file_time
            event_type,
            actor_login,
            repo_name,
            created_at,  # created_at
            updated_at,  # updated_at  
            action,
            comment_id,  # comment_id
            body,
            path,  # path
            position,  # position
            line,  # line
            ref,  # ref
            ref_type,  # ref_type
            actor_login,  # creator_user_login
            number,
            title,
            [],  # labels
            state,
            0,  # locked
            '',  # assignee
            [],  # assignees
            0,  # comments
            'NONE',  # author_association
            default_datetime,  # closed_at
            default_datetime,  # merged_at
            '',  # merge_commit_sha
            [],  # requested_reviewers
            [],  # requested_teams
            0,  # merged
            0,  # mergeable
            'unknown',  # mergeable_state
            '',  # merged_by
            0,  # review_comments
            0,  # maintainer_can_modify
            0,  # commits
            0,  # additions
            0,  # deletions
            0,  # changed_files
            f"commit{random.randint(1000000, 9999999)}",  # commit_id
            f"original{random.randint(1000000, 9999999)}",  # original_commit_id
            '',  # member_login
            '',  # release_tag_name
            '',  # release_name
            'none'  # review_state
        )
        events.append(other_event)
    
    return events

def insert_dummy_data(client: Client) -> None:
    """Insert dummy data into the github_events table."""
    
    # Check if table already has data
    result = client.query("SELECT COUNT(*) FROM github_events")
    count = result.result_rows[0][0]
    
    if count > 0:
        logger.info(f"Table already contains {count} records, skipping data insertion")
        return
    
    logger.info("Generating dummy data...")
    dummy_data = generate_dummy_data(1000)
    
    logger.info("Inserting dummy data...")
    client.insert(
        'github_events',
        dummy_data,
        column_names=[
            'file_time', 'event_type', 'actor_login', 'repo_name', 'created_at', 'updated_at',
            'action', 'comment_id', 'body', 'path', 'position', 'line', 'ref', 'ref_type',
            'creator_user_login', 'number', 'title', 'labels', 'state', 'locked', 'assignee',
            'assignees', 'comments', 'author_association', 'closed_at', 'merged_at',
            'merge_commit_sha', 'requested_reviewers', 'requested_teams', 'merged', 'mergeable',
            'mergeable_state', 'merged_by', 'review_comments', 'maintainer_can_modify',
            'commits', 'additions', 'deletions', 'changed_files', 'commit_id',
            'original_commit_id', 'member_login', 'release_tag_name', 'release_name', 'review_state'
        ]
    )
    
    # Verify insertion
    result = client.query("SELECT COUNT(*) FROM github_events")
    count = result.result_rows[0][0]
    logger.info(f"Successfully inserted {count} records")
    
    # Show sample data by repository
    result = client.query("""
        SELECT repo_name, event_type, COUNT(*) as count
        FROM github_events 
        GROUP BY repo_name, event_type 
        ORDER BY repo_name, count DESC
    """)
    
    logger.info("Sample data by repository:")
    for row in result.result_rows:
        logger.info(f"  {row[0]} - {row[1]}: {row[2]} events")

def main():
    """Main initialization function."""
    logger.info("Starting database initialization...")
    
    try:
        # Connect to ClickHouse using HTTP interface
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_HTTP_PORT,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DB
        )
        
        # Wait for ClickHouse to be ready
        if not wait_for_clickhouse(client):
            logger.error("ClickHouse is not ready, exiting")
            return
        
        # Create table
        create_table_if_not_exists(client)
        
        # Insert dummy data
        insert_dummy_data(client)
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    main() 
