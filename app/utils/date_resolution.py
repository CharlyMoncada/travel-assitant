import datetime
from datetime import datetime, timedelta

def get_current_date_resolution_context() -> dict:
    now = datetime.now()
    current_datetime = now.strftime("%A, %d %B %Y at %H:%M")
    current_date_iso = now.strftime("%Y-%m-%d")

    # Precomputar fechas relativas comunes
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after_tomorrow = (now + timedelta(days=2)).strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    day_before_yesterday = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    in_3_days = (now + timedelta(days=3)).strftime("%Y-%m-%d")
    in_5_days = (now + timedelta(days=5)).strftime("%Y-%m-%d")
    in_7_days = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    in_1h = (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    in_2h = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    in_4h = (now + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M")
    in_half_hour = (now + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
    next_week = (now + timedelta(days=7)).strftime("%Y-%m-%d")
    
    days_to_saturday = (5 - now.weekday()) % 7
    if days_to_saturday == 0:
        days_to_saturday = 7
    this_weekend = (now + timedelta(days=days_to_saturday)).strftime("%Y-%m-%d")

    next_weekday_dates = {}
    for wd in range(7):
        days_ahead = (wd - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        next_weekday_dates[wd] = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return {
        "current_datetime": current_datetime,
        "current_date_iso": current_date_iso,
        "tomorrow": tomorrow,
        "day_after_tomorrow": day_after_tomorrow,
        "yesterday": yesterday,
        "day_before_yesterday": day_before_yesterday,
        "in_3_days": in_3_days,
        "in_5_days": in_5_days,
        "in_7_days": in_7_days,
        "in_1h": in_1h,
        "in_2h": in_2h,
        "in_4h": in_4h,
        "in_half_hour": in_half_hour,
        "next_week": next_week,
        "this_weekend": this_weekend,
        "next_weekday_dates": next_weekday_dates,
    }

def get_date_resolution_prompt_directives(ctx: dict) -> str:
    return (
        f"DATE RESOLUTION: Reference date is {ctx['current_date_iso']} ({ctx['current_datetime']}). "
        f"Key offsets: tomorrow={ctx['tomorrow']}, day_after={ctx['day_after_tomorrow']}, yesterday={ctx['yesterday']}. "
        "Resolve any relative date or time expression in user requests to exact ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM) before calling tools."
    )
