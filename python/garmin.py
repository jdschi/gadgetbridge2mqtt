# Watch specific details are stored here. Location is important.
# Additional sensors to publish can be added here using this example from the code as a template. Note
# that all lines typically require modification.
#self.sensor_monthly_calories =         {
#            "name": "Monthly Calories",
#            "unique_id": "monthly_calories",
#            "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/calories/monthly",
#            "device_class": "energy",
#            "icon": "mdi:fire",
#            "unit_of_measurement": "kcal",
#            "query": self.query_monthly_calories,
#        }
self.watch_type_activity = "GARMIN_ACTIVITY_SAMPLE"
self.watch_type_heart_rate = "GARMIN_ACTIVITY_SAMPLE"
self.watch_type_spo2 = "MOYOUNG_SPO2_SAMPLE"
self.heart_rate_column = "HEART_RATE"
self.distance_column = "DISTANCE_CM"                # Each device uses its own column name in the database
self.calories_column = "ACTIVE_CALORIES"
self.heart_rate_column = "HEART_RATE"
self.spo2_column = "SPO2"
self.sensors = [
    self.sensor_device_id,
#                self.sensor_user_birthday,
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
]
# Additional query definitions may be added here as needed above. Here is an example
#def query_monthly_steps(self, cursor) -> Any:
#    today = datetime.now().date()
#    month_start = today.replace(day=1)
#    month_start_ts = int(
#        datetime.combine(month_start, datetime.min.time()).timestamp()
#    )
#    device_id = self.get_device_id(cursor)
#    query = f"""
#        SELECT SUM(STEPS)
#        FROM {self.watch_type_activity}
#        WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
#    """
#    cursor.execute(query, (month_start_ts, device_id))
#    return cursor.fetchone()[0] or 0
