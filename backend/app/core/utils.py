from datetime import datetime, timedelta

DEFAULT_MONTH_WINDOW = 6

def format_time_difference(seconds):
    """Format a time difference in seconds to a human-readable string."""
    if not seconds:
        return "Unknown"
        
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 and not parts:  # Only show seconds if less than a minute
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
    if not parts:
        return "Just now"
        
    return ", ".join(parts)

def format_time_delta(delta: timedelta) -> str:
    """Convert timedelta to human-readable string (e.g., '2 days 3 hours')"""
    seconds = delta.total_seconds()
    periods = [
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    
    parts = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            parts.append(f"{int(period_value)} {period_name}{'s' if period_value != 1 else ''}")
    
    return " ".join(parts[:2]) if parts else "0 seconds"


def default_start_date(months: int = DEFAULT_MONTH_WINDOW, end: datetime | None = None) -> str:
    """Return ISO date string representing `months` months ago (approximate 30 days per month)."""
    end_dt = end or datetime.utcnow()
    start_dt = end_dt - timedelta(days=30 * months)
    return start_dt.strftime("%Y-%m-%d")
