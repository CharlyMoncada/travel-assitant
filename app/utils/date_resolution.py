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
        "DATE RESOLUTION DIRECTIVE: When the user mentions a date or time, follow these two steps internally before calling any tool:\n\n"
        "   STEP 1 — Translate the date expression to English (internal reasoning language):\n"
        "     'hoy'                             = 'today'\n"
        "     'manana' / 'mañana'               = 'tomorrow'\n"
        "     'pasado manana' / 'pasado mañana' = 'day after tomorrow'\n"
        "     'ayer'                            = 'yesterday'\n"
        "     'anteayer' / 'antes de ayer'      = 'day before yesterday'\n"
        "     'dentro de 1 dia' / 'en 1 dia'   = 'in 1 day' (= tomorrow)\n"
        "     'dentro de N dias'                = 'in N days'\n"
        "     'en una hora' / 'en 1 hora'       = 'in 1 hour'\n"
        "     'en media hora' / 'en 30 minutos' = 'in half an hour'\n"
        "     'en N horas'                      = 'in N hours'\n"
        "     'esta semana' / 'esta semana'      = 'this week' (= today)\n"
        "     'la semana que viene' / 'la proxima semana' / 'la próxima semana' = 'next week'\n"
        "     'este fin de semana' / 'el finde' = 'this weekend'\n"
        "     'el lunes'                        = 'next Monday'\n"
        "     'el martes'                       = 'next Tuesday'\n"
        "     'el miercoles' / 'el miércoles'   = 'next Wednesday'\n"
        "     'el jueves'                       = 'next Thursday'\n"
        "     'el viernes'                      = 'next Friday'\n"
        "     'el sabado' / 'el sábado'         = 'next Saturday'\n"
        "     'el domingo'                      = 'next Sunday'\n\n"
        "   STEP 2 — Map the English expression to its exact pre-computed date (copy the value, do not recalculate):\n"
        f"     'today'              = {ctx['current_date_iso']}\n"
        f"     'tomorrow'           = {ctx['tomorrow']}\n"
        f"     'day after tomorrow' = {ctx['day_after_tomorrow']}\n"
        f"     'yesterday'          = {ctx['yesterday']}\n"
        f"     'day before yesterday' = {ctx['day_before_yesterday']}\n"
        f"     'in 3 days'          = {ctx['in_3_days']}\n"
        f"     'in 5 days'          = {ctx['in_5_days']}\n"
        f"     'in 7 days'          = {ctx['in_7_days']}\n"
        f"     'in 1 hour'          = {ctx['in_1h']}\n"
        f"     'in half an hour'    = {ctx['in_half_hour']}\n"
        f"     'in 2 hours'         = {ctx['in_2h']}\n"
        f"     'in 4 hours'         = {ctx['in_4h']}\n"
        f"     'next week'          = {ctx['next_week']}\n"
        f"     'this weekend'       = {ctx['this_weekend']}\n"
        f"     'next Monday'        = {ctx['next_weekday_dates'][0]}\n"
        f"     'next Tuesday'       = {ctx['next_weekday_dates'][1]}\n"
        f"     'next Wednesday'     = {ctx['next_weekday_dates'][2]}\n"
        f"     'next Thursday'      = {ctx['next_weekday_dates'][3]}\n"
        f"     'next Friday'        = {ctx['next_weekday_dates'][4]}\n"
        f"     'next Saturday'      = {ctx['next_weekday_dates'][5]}\n"
        f"     'next Sunday'        = {ctx['next_weekday_dates'][6]}\n"
        "     'in N days' (arbitrary N not listed above): add N days to today's date.\n"
        "     'in N hours' (arbitrary N not listed above): add N hours to the current time.\n"
    )
