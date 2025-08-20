self.watch_type_activity = "COLMI_ACTIVITY_SAMPLE"
self.watch_type_sleep = "COLMI_SLEEP_STAGE_SAMPLE"
self.watch_type_spo2 = "COLMI_SPO2_SAMPLE"
self.watch_type_heart_rate = "COLMI_HEART_RATE_SAMPLE"
self.distance_column = "DISTANCE"
self.calories_column = "CALORIES"
self.spo2_column = "SPO2"
self.heart_rate_column = "HEART_RATE"
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
    self.sensor_daily_distance,
    self.sensor_weekly_distance,
    self.sensor_monthly_distance,
    self.sensor_daily_calories,
    self.sensor_weekly_calories,
    self.sensor_monthly_calories,
    self.sensor_spO2,
    self.sensor_deep_sleep_duration,
    self.sensor_light_sleep_duration,
    self.sensor_rem_sleep_duration,
]
