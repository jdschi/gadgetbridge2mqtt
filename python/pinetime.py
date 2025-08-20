self.watch_type_activity = "PINE_TIME_ACTIVITY_SAMPLE"  # Table where activities are stored
self.watch_type_heart_rate = "PINE_TIME_ACTIVITY_SAMPLE"
self.heart_rate_column = "HEART_RATE"                   # Column name for heart rate
self.sensors = [
    self.sensor_device_id,
#    self.sensor_user_birthday,
    self.sensor_user_age,
    self.sensor_battery_level,
    self.sensor_latest_heart_rate,
    self.sensor_avg_heart_rate_24h,
    self.sensor_min_heart_rate_24h,
    self.sensor_max_heart_rate_24h,
    self.sensor_daily_steps,
    self.sensor_weekly_steps,
    self.sensor_monthly_steps,
    self.sensor_latest_heart_rate,
]
