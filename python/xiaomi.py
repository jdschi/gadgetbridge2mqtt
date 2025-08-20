#----------------------------------------------------------------------------------------------------------------------
# ------------- COMPLETELY UNTESTED. TAKEN FROM https://github.com/Progaros/GadgetbridgeMqtt/blob/main/main.py --------
#----------------------------------------------------------------------------------------------------------------------

# Each new sensor requires at least 3 additions to this file: (1) a new MQTT publication "self.sensor_new_sensor",
# (2) this new sensor added to the list of self sensors, and (3) a query definition that depends on the details
# of how the data are stored in the database. Examples are given below. It might also be useful to define
# new activities or columns for future purposes, but not strictly necessary here.

# The new query definitions are not yet working.

# Any added sensors need definitions compatible with the query definitions below. The template is from an
# example in the main program. The order of MQTT sensor, watch details, and query definitions is important.
# To show up in HA, the new sensor must be added to the list of self.sensors.
# self.sensor_monthly_calories =         {
#             "name": "Monthly Calories",
#             "unique_id": "monthly_calories",
#             "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/calories/monthly",
#             "device_class": "energy",
#             "icon": "mdi:fire",
#             "unit_of_measurement": "kcal",
#             "query": self.query_monthly_calories,
#         }

self.sensor_weight =                {
                "name": "Weight",
                "unique_id": "weight",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/weight",
                "unit_of_measurement": "kg",
                "icon": "mdi:scale-bathroom",
                "state_class": "measurement",
                "query": self.query_latest_weight,
        },
self.sensor_resting_hr =            {
                "name": "Resting Heart Rate",
                "unique_id": "hr_resting",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/resting",
                "unit_of_measurement": "bpm",
                "icon": "mdi:heart-pulse",
                "state_class": "measurement",
                "query": self.query_hr_resting,
            },
self.sensor_max_hr =            {
                "name": "Max Heart Rate",
                "unique_id": "hr_max",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/max",
                "unit_of_measurement": "bpm",
                "icon": "mdi:heart-pulse",
                "state_class": "measurement",
                "query": self.query_hr_max,
            },
self.sensor_avg_hr =            {
                "name": "Average Heart Rate",
                "unique_id": "hr_avg",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/avg",
                "unit_of_measurement": "bpm",
                "icon": "mdi:heart-pulse",
                "state_class": "measurement",
                "query": self.query_hr_avg,
            },
self.sensor_calories =            {
                "name": "Calories",
                "unique_id": "calories",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/calories",
                "unit_of_measurement": "kcal",
                "icon": "mdi:fire",
                "state_class": "total_increasing",
                "query": self.query_calories,
            },
self.sensor_is_awake =            {
                "name": "Is Awake",
                "unique_id": "is_awake",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/is_awake",
                "icon": "mdi:power-sleep",
                "device_class": "enum",
                "query": self.query_is_awake,
            },
self.sensor_total_sleep_duration =            {
                "name": "Total Sleep Duration",
                "unique_id": "total_sleep_duration",
                "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/total_sleep_duration",
                "unit_of_measurement": "h",
                "icon": "mdi:sleep",
                "state_class": "measurement",
                "query": self.query_total_sleep_duration,
            },


self.watch_type_activity = "XIAOMI_ACTIVITY_SAMPLE"
self.watch_type_heart_rate = "XIAOMI_ACTIVITY_SAMPLE"
self.heart_rate_column = "HEART_RATE"
self.sensors = [
    self.sensor_device_id,
#                self.sensor_user_birthday,
    self.sensor_user_age,
    self.sensor_battery_level,
    self.sensor_latest_heart_rate,
    self.sensor_daily_steps,
    self.sensor_weekly_steps,
    self.sensor_monthly_steps,
# Defined here:
    self.sensor_weight,
    self.sensor_resting_hr,
    self.sensor_max_hr,
    self.sensor_avg_hr,
    self.sensor_is_awake,
    self.sensor_calories,
    self.sensor_total_sleep_duration,
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
