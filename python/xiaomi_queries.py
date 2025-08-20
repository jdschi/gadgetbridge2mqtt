def query_latest_weight(self, cursor) -> Any:
    cursor.execute(
        "SELECT WEIGHT_KG FROM MI_SCALE_WEIGHT_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row[0] if row else None

def query_hr_resting(self, cursor) -> Any:
    cursor.execute(
        "SELECT HR_RESTING FROM XIAOMI_DAILY_SUMMARY_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row[0] if row else None

def query_hr_max(self, cursor) -> Any:
    cursor.execute(
        "SELECT HR_MAX FROM XIAOMI_DAILY_SUMMARY_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row[0] if row else None

def query_hr_avg(self, cursor) -> Any:
    cursor.execute(
        "SELECT HR_AVG FROM XIAOMI_DAILY_SUMMARY_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row[0] if row else None

def query_calories(self, cursor) -> Any:
    cursor.execute(
        "SELECT CALORIES FROM XIAOMI_DAILY_SUMMARY_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    return row[0] if row else None

def query_is_awake(self, cursor) -> Any:
    cursor.execute(
        "SELECT IS_AWAKE FROM XIAOMI_SLEEP_TIME_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    # Return as boolean or string for Home Assistant
    return not bool(row[0]) if row else None  # inverted

def query_total_sleep_duration(self, cursor) -> Any:
    cursor.execute(
        "SELECT TOTAL_DURATION FROM XIAOMI_SLEEP_TIME_SAMPLE ORDER BY TIMESTAMP DESC LIMIT 1"
    )
    row = cursor.fetchone()
    # Convert minutes to hours, round to 2 decimals
    return round(row[0] / 60, 2) if row and row[0] is not None else None
