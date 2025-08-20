#!/usr/bin/env python3
"""
Gadgetbridge MQTT Step Counter Integration
Extracts sensor data from Gadgetbridge SQLite database and publishes to Home Assistant via MQTT
Home Assistant is not necessary, of course, since anything that utilize the MQTT broker should work,
but this has not been tested.
On startup, data are published. Thereafter, publication is triggered by publishing the payload "publish"
to the topic "gadgetbridge/command"
The docker compose file requires as input the MQTT location, port and credentials.
It also requires two volumes: /data where the Gadgetbridge.db file is stored, and
/code_dir where the python code is stored, which includes this main.py file, healthcheck,py, and
various watch_type.py files for specific gadgets.
"""

import os
import sqlite3
import json
import logging
import time
from datetime import datetime, timedelta, timezone
#from zoneinfo import ZoneInfo  # Python 3.9+
from typing import Dict, Any
import asyncio
import aiomqtt
import re
import pytz
import shutil
import tempfile
from contextlib import contextmanager
import importlib.util
from pathlib import Path

@contextmanager
def open_db_snapshot(db_path):
    """Context manager: open a stable snapshot of the SQLite DB even if the source file is being replaced."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB file not found: {db_path}")

    tmp_path = None
    try:
        # Copy DB to a temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copy2(db_path, tmp.name)
            tmp_path = tmp.name

        # Open snapshot in read-only mode
        conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
        yield conn  # Let caller use the connection
    except Exception:
        logging.exception("Failed to open DB snapshot")
        raise
    finally:
        # Always close and clean up
        try:
            if 'conn' in locals():
                conn.close()
        except Exception:
            pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as e:
                logging.warning(f"Could not remove temp DB snapshot: {e}")

class GadgetbridgeMQTTPublisher:
    def __init__(self):
        self.setup_logging()
        self.db_path = os.getenv("GADGETBRIDGE_DB_PATH", "/data/Gadgetbridge.db")
        self.load_config()
        self.mqtt_client = None
# WATCH_TYPE must be given in the environment of the docker compose file.
# It is used to find the device_id and name of the device, and the available data.
# The alias would be better for user control, but doesn't seem reliable in GB (Settings-> three dots -> Alias)
        self.watch_type = os.getenv("WATCH_TYPE","error").lower()
        if self.watch_type == "error":
            print('No watch type specified in docker.')
        self.mac_address = os.getenv("MAC_ADDRESS","error")
        if self.mac_address == "error":
            print('No watch MAC address is specified in docker.')
        self.device_name = self.get_device_alias_initial() # Used to create the first subtopic for the MQTT sensors
        self.user_name = self.get_username_initial() # Used to create the first subtopic for the MQTT sensors
        self.manufacturer = self.get_manufacturer_initial()
        print('Watch type:',self.watch_type)
        print('User name:',self.user_name)
        print('Device name:',self.device_name)
        print('MAC adress:',self.mac_address)

# ----------------- Sensors publishable to MQTT --------------------------
# These sensors are universal to gadgetbridge

        self.sensor_device_id =           {
                    "name": "Device ID",
                    "unique_id": "device_id",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/device_id",
                    "query": self.get_device_id,
                }
        self.sensor_user_birthday =       {
                    "name": "User Birthday",
                    "unique_id": "user_birthday",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/user_birthday",
                    "query": self.get_birthdate
                }
        self.sensor_user_age =       {
                    "name": "User Age",
                    "unique_id": "user_age",
                    "unit_of_measurement": "years",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/user_age",
                    "query": self.get_age
                }
        self.sensor_battery_level =        {
                    "name": "Battery Level",
                    "unique_id": "battery_level",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/battery",
                    "unit_of_measurement": "%",
                    "icon": "mdi:battery",
                    "device_class": "battery",
                    "query": self.query_battery_level,
                }

# These sensors are somewhat watch specific
        self.sensor_latest_heart_rate =           {
                    "name": "Latest Heart Rate",
                    "unique_id": "latest_heart_rate",
                    "unit_of_measurement": "bpm",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/latest",
                    "query": self.query_latest_heart_rate,
                }
        self.sensor_avg_heart_rate_24h =           {
                    "name": "Average Heart Rate Last 24hr",
                    "unique_id": "average_heart_rate",
                    "unit_of_measurement": "bpm",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/average",
                    "query": self.query_avg_heart_rate_24h,
                }
        self.sensor_max_heart_rate_24h =           {
                    "name": "Maximum Heart Rate Last 24hr",
                    "unique_id": "max_heart_rate",
                    "unit_of_measurement": "bpm",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/maximum",
                    "query": self.query_max_heart_rate_24h,
                }
        self.sensor_min_heart_rate_24h =           {
                    "name": "Minimum Heart Rate Last 24hr",
                    "unique_id": "min_heart_rate",
                    "unit_of_measurement": "bpm",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/heart_rate/minimum",
                    "query": self.query_min_heart_rate_24h,
                }
        self.sensor_daily_steps =        {
                    "name": "Daily Steps",
                    "unique_id": "daily_steps",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/steps/daily",
                    "unit_of_measurement": "steps",
                    "icon": "mdi:walk",
                    "state_class": "total_increasing",
                    "query": self.query_daily_steps,
                }
        self.sensor_weekly_steps =       {
                    "name": "Weekly Steps",
                    "unique_id": "weekly_steps",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/steps/weekly",
                    "unit_of_measurement": "steps",
                    "icon": "mdi:walk",
                    "state_class": "total",
                    "query": self.query_weekly_steps,
                }
        self.sensor_monthly_steps =       {
                    "name": "Monthly Steps",
                    "unique_id": "monthly_steps",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/steps/monthly",
                    "unit_of_measurement": "steps",
                    "icon": "mdi:walk",
                    "state_class": "total",
                    "query": self.query_monthly_steps,
                }
        self.sensor_daily_distance =        {
                    "name": "Daily Distance",
                    "unique_id": "daily_distance",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/distance/daily",
                    "device_class": "distance",
                    "icon": "mdi:walk",
                    "unit_of_measurement": "meters",
                    "query": self.query_daily_distance,
                }
        self.sensor_weekly_distance =        {
                    "name": "Weekly Distance",
                    "unique_id": "weekly_distance",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/distance/weekly",
                    "device_class": "distance",
                    "icon": "mdi:walk",
                    "unit_of_measurement": "meters",
                    "query": self.query_weekly_distance,
                }
        self.sensor_monthly_distance =       {
                    "name": "Monthly Distance",
                    "unique_id": "monthly_distance",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/distance/monthly",
                    "device_class": "distance",
                    "icon": "mdi:walk",
                    "unit_of_measurement": "meters",
                    "query": self.query_monthly_distance,
                }
        self.sensor_daily_calories =          {
                    "name": "Daily Calories",
                    "unique_id": "daily_calories",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/calories/daily",
                    "device_class": "energy",
                    "icon": "mdi:fire",
                    "unit_of_measurement": "kcal",
                    "query": self.query_daily_calories,
                }
        self.sensor_weekly_calories =          {
                    "name": "Weekly Calories",
                    "unique_id": "weekly_calories",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/calories/weekly",
                    "device_class": "energy",
                    "icon": "mdi:fire",
                    "unit_of_measurement": "kcal",
                    "query": self.query_weekly_calories,
                }
        self.sensor_monthly_calories =         {
                    "name": "Monthly Calories",
                    "unique_id": "monthly_calories",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/calories/monthly",
                    "device_class": "energy",
                    "icon": "mdi:fire",
                    "unit_of_measurement": "kcal",
                    "query": self.query_monthly_calories,
                }
        self.sensor_spO2 =           {
                    "name": "Partial pressure Oxygen",
                    "unique_id": "spO2",
                    "unit_of_measurement": "%",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/spo2",
                    "query": self.get_latest_spO2,
                }
        self.sensor_deep_sleep_duration =           {
                    "name": "Deep Sleep Duration",
                    "unique_id": "deep_sleep_duration",
                    "unit_of_measurement": "h",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/deep_sleep_duration",
                    "query": lambda cursor: self.query_sleep_stage_durations(cursor)[3]
                }
        self.sensor_light_sleep_duration =           {
                    "name": "Light Sleep Duration",
                    "unique_id": "light_sleep_duration",
                    "unit_of_measurement": "h",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/light_sleep_duration",
                    "query": lambda cursor: self.query_sleep_stage_durations(cursor)[2]
                }
        self.sensor_rem_sleep_duration =           {
                    "name": "REM Sleep Duration",
                    "unique_id": "rem_sleep_duration",
                    "unit_of_measurement": "h",
                    "state_topic": f"gadgetbridge/{self.user_name}_{self.device_name}/rem_sleep_duration",
                    "query": lambda cursor: self.query_sleep_stage_durations(cursor)[1]
                }

# Defines the database table and column names appropriate for that device.
# Also includes the sensors available.

        with open(f"{self.watch_type}.py") as watch:
            exec(watch.read())

# ----------------- Calls to the database for sensor data ------------------------------------

# More sensors and hints are available here: https://gadgetbridge.org/internals/development/data-management/
# However, it is probably necessary to examine the database for better information (e.g., through DBbrowser for SQLITE)





    # ---------------- INITIAL DB fetch (one-shot, tolerates missing DB) ----------------
    def get_device_alias_initial(self):
        try:
            with open_db_snapshot(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT NAME FROM DEVICE WHERE IDENTIFIER LIKE ? LIMIT 1",
                    (self.mac_address,),
                )
                row = cur.fetchone()
                return re.sub(r"\W+", "_", row[0]).lower() if row else "fitness_tracker"
        except Exception:
            return "fitness_tracker"

    def get_username_initial(self):
        try:
            with open_db_snapshot(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT NAME FROM USER LIMIT 1")
                row = cur.fetchone()
                return row[0] if row else "fitness_tracker"
        except Exception:
            return "fitness_tracker"

    def get_manufacturer_initial(self):
        try:
            with open_db_snapshot(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT MANUFACTURER FROM DEVICE WHERE IDENTIFIER LIKE ? LIMIT 1",
                    (self.mac_address,),)
                row = cur.fetchone()
                return row[0] if row else "GadgetBridge"
        except Exception:
            return "GadgetBridge"

    # ---------------- SENSOR QUERIES (cursor-based only) ----------------
    def get_device_id(self, cursor) -> Any:
        cursor.execute(
            "SELECT _id FROM DEVICE WHERE IDENTIFIER LIKE ? LIMIT 1",
            (self.mac_address,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None

    def get_birthdate(self, cursor) -> Any:
        cursor.execute("SELECT BIRTHDAY FROM USER LIMIT 1")
        row = cursor.fetchone()
        if row and row[0]:
            return datetime.fromtimestamp(row[0] / 1000).strftime("%Y-%m-%d")
        return None

    def get_age(self, cursor) -> Any:
        cursor.execute("SELECT BIRTHDAY FROM USER LIMIT 1")
        row = cursor.fetchone()
        now = datetime.now().timestamp()
        age_ts = now - int(row[0]/1000)
        age_years = round(float(age_ts/60/60/24/365.25), 2)
#        print('age_years=', age_years)
        if row and row[0]:
            return age_years
        return None

    def query_battery_level(self, cursor) -> Any:
        device_id = self.get_device_id(cursor)
        cursor.execute(
            "SELECT LEVEL FROM BATTERY_LEVEL WHERE DEVICE_ID = ? "
            "ORDER BY TIMESTAMP DESC LIMIT 1",
            (device_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def query_daily_steps(self, cursor) -> Any:
        today = datetime.now().date()
        today_start = int(datetime.combine(today, datetime.min.time()).timestamp())
        today_end = int(datetime.combine(today, datetime.max.time()).timestamp())
        device_id = self.get_device_id(cursor)
        query = f"""
            SELECT SUM(STEPS)
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND TIMESTAMP <= ? AND DEVICE_ID = ?
        """
        cursor.execute(query, (today_start, today_end, device_id))
        return cursor.fetchone()[0] or 0

    def query_daily_distance(self, cursor) -> Any:
        today = datetime.now().date()
        today_start = int(datetime.combine(today, datetime.min.time()).timestamp())
        today_end = int(datetime.combine(today, datetime.max.time()).timestamp())
        device_id = self.get_device_id(cursor)
        column = self.distance_column
        query = f"""
            SELECT SUM({column})
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND TIMESTAMP <= ? AND DEVICE_ID = ?
        """
        cursor.execute(query, (today_start, today_end, device_id))
        return cursor.fetchone()[0] or 0

    def query_daily_calories(self, cursor) -> Any:
        today = datetime.now().date()
        today_start = int(datetime.combine(today, datetime.min.time()).timestamp())
        today_end = int(datetime.combine(today, datetime.max.time()).timestamp())
        device_id = self.get_device_id(cursor)
        column = self.calories_column
        query = f"""
            SELECT SUM({column})
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND TIMESTAMP <= ? AND DEVICE_ID = ?
        """
        cursor.execute(query, (today_start, today_end, device_id))
        return cursor.fetchone()[0] or 0

    def query_weekly_steps(self, cursor) -> Any:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_start_ts = int(datetime.combine(week_start, datetime.min.time()).timestamp())
        device_id = self.get_device_id(cursor)
        query = f"""
            SELECT SUM(STEPS)
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
        """
        cursor.execute(query, (week_start_ts, device_id))
        return cursor.fetchone()[0] or 0

    def query_weekly_distance(self, cursor) -> Any:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_start_ts = int(datetime.combine(week_start, datetime.min.time()).timestamp())
        device_id = self.get_device_id(cursor)
        column = self.distance_column
        query = f"""
            SELECT SUM({column})
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
        """
        cursor.execute(query, (week_start_ts, device_id))
        return cursor.fetchone()[0] or 0

    def query_weekly_calories(self, cursor) -> Any:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_start_ts = int(datetime.combine(week_start, datetime.min.time()).timestamp())
        device_id = self.get_device_id(cursor)
        column = self.calories_column
        query = f"""
             SELECT SUM({column})
             FROM {self.watch_type_activity}
             WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
         """
        cursor.execute(query, (week_start_ts, device_id))
        return cursor.fetchone()[0] or 0

    def query_monthly_steps(self, cursor) -> Any:
       today = datetime.now().date()
       month_start = today.replace(day=1)
       month_start_ts = int(
           datetime.combine(month_start, datetime.min.time()).timestamp()
       )
       device_id = self.get_device_id(cursor)
       query = f"""
            SELECT SUM(STEPS)
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
        """
       cursor.execute(query, (month_start_ts, device_id))
       return cursor.fetchone()[0] or 0

    def query_monthly_distance(self, cursor) -> Any:
       today = datetime.now().date()
       month_start = today.replace(day=1)
       month_start_ts = int(
           datetime.combine(month_start, datetime.min.time()).timestamp()
       )
       device_id = self.get_device_id(cursor)
       column = self.distance_column
       query = f"""
            SELECT SUM({column})
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
        """
       cursor.execute(query, (month_start_ts, device_id))
       return cursor.fetchone()[0] or 0

    def query_monthly_calories(self, cursor) -> Any:
       today = datetime.now().date()
       month_start = today.replace(day=1)
       month_start_ts = int(
           datetime.combine(month_start, datetime.min.time()).timestamp()
       )
       device_id = self.get_device_id(cursor)
       column = self.calories_column
       query = f"""
            SELECT SUM({column})
            FROM {self.watch_type_activity}
            WHERE TIMESTAMP >= ? AND DEVICE_ID = ?
        """
       cursor.execute(query, (month_start_ts, device_id))
       return cursor.fetchone()[0] or 0

    def get_latest_spO2(self,cursor) ->  Any:
        """Fetch SPO2 from table where TYPE_NAME contains whatever value the WATCH_TYPE environment variable is given in docker compose"""
        cursor.execute(
            f"""
            SELECT {self.spo2_column} FROM {self.watch_type_spo2} ORDER BY TIMESTAMP DESC LIMIT 1
        """
        )
        return cursor.fetchone()[0]

    def query_latest_heart_rate(self, cursor) -> Any:
        query = f"""
            SELECT {self.heart_rate_column}
            FROM {self.watch_type_heart_rate}
            WHERE {self.heart_rate_column} < 255 AND {self.heart_rate_column} > 1
            ORDER BY TIMESTAMP DESC
            LIMIT 1
        """
        cursor.execute(query)
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def query_avg_heart_rate_24h(self, cursor) -> Any:
        # Calculate UNIX timestamp for 24 hours ago
        now = int(datetime.now().timestamp())
        day_ago = now - 24 * 60 * 60  # 86,400 seconds

        query = f"""
            SELECT AVG({self.heart_rate_column})
            FROM {self.watch_type_heart_rate}
            WHERE {self.heart_rate_column} < 255 AND {self.heart_rate_column} > 1
            AND TIMESTAMP >= ?
        """
        cursor.execute(query, (day_ago,))
        row = cursor.fetchone()
        return round(float(row[0]), 2) if row and row[0] is not None else None

    def query_max_heart_rate_24h(self, cursor) -> Any:
        # Calculate UNIX timestamp for 24 hours ago
        now = int(datetime.now().timestamp())
        day_ago = now - 24 * 60 * 60  # 86,400 seconds

        query = f"""
            SELECT MAX({self.heart_rate_column})
            FROM {self.watch_type_heart_rate}
            WHERE {self.heart_rate_column} < 255 AND {self.heart_rate_column} > 1
            AND TIMESTAMP >= ?
        """
        cursor.execute(query, (day_ago,))
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def query_min_heart_rate_24h(self, cursor) -> Any:
        # Calculate UNIX timestamp for 24 hours ago
        now = int(datetime.now().timestamp())
        day_ago = now - 24 * 60 * 60  # 86,400 seconds

        query = f"""
            SELECT MIN({self.heart_rate_column})
            FROM {self.watch_type_heart_rate}
            WHERE {self.heart_rate_column} < 255 AND {self.heart_rate_column} > 1
            AND TIMESTAMP >= ?
        """
        cursor.execute(query, (day_ago,))
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] is not None else None

    def get_local_noon_window_utc_ms(self, timezone_str="America/Chicago"):
        local_tz = pytz.timezone(timezone_str)
        now_local = datetime.now(local_tz)

        # Noon today in local time
        noon_today_local = local_tz.localize(
            datetime(now_local.year, now_local.month, now_local.day, 12)
        )

        # Noon yesterday
        noon_yesterday_local = noon_today_local - timedelta(days=1)

        # Convert to UTC
        noon_today_utc = noon_today_local.astimezone(pytz.utc)
        noon_yesterday_utc = noon_yesterday_local.astimezone(pytz.utc)

        # Convert to ms
        ts_start_utc_ms = int(noon_yesterday_utc.timestamp() * 1000)
        ts_end_utc_ms = int(noon_today_utc.timestamp() * 1000)

        return ts_start_utc_ms, ts_end_utc_ms

    def query_sleep_stage_durations(self, cursor) -> dict:
        ts_start, ts_end = self.get_local_noon_window_utc_ms("America/Chicago")
        results = {}
        for stage in range(4):  # stages 0, 1, 2, 3
            cursor.execute(
                f"""
                SELECT SUM(DURATION)
                FROM {self.watch_type_sleep}
                WHERE TIMESTAMP >= ? AND TIMESTAMP < ? AND STAGE = ?
                """,
                (ts_start, ts_end, stage)
            )
            row = cursor.fetchone()
            total_min = float(row[0]) if row and row[0] is not None else 0.0
            results[stage] = round(total_min / (60),2)  # convert min → hours

        return results

# Untested Xiaomi queries:
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


# -------------------------------- Logging and MQTT setup ----------------------------

    def setup_logging(self):
        """Setup logging configuration (console only)"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def load_config(self):
        """Load MQTT configuration from environment variables"""
        self.mqtt_config = {
            "broker": os.getenv("MQTT_BROKER", "localhost"),
            "port": int(os.getenv("MQTT_PORT", "1883")),
            "username": os.getenv("MQTT_USERNAME", ""),
            "password": os.getenv("MQTT_PASSWORD", ""),
        }

# ------------------------------ Configure Home Assistant automatic discovery -----------------------

# Need to make the code more robust by creating a variable to ensure that the discovery topic and unique_id match.
# Probably also more consistency with entity names, etc.

    async def publish_home_assistant_discovery(
        self, entity_type: str, entity_id: str, config: Dict
    ):
        """Publish Home Assistant MQTT discovery configuration asynchronously"""
        discovery_topic = (
            f"homeassistant/{entity_type}/{self.mac_address.replace(':','')}_{entity_id}/config"
        )
        try:
            await self.mqtt_client.publish(
                discovery_topic, json.dumps(config), qos=0, retain=True
            )
            self.logger.info(f"Published discovery config for {entity_id}")
        except Exception as e:
            self.logger.error(f"Failed to publish discovery config: {e}")

    async def setup_home_assistant_entities(self):
        """Setup Home Assistant entities via MQTT discovery"""
        device_info = {
            "identifiers": [f"{self.mac_address.replace(':','')}"],
            "name": f"Gadgetbridge {self.user_name.title()} {self.device_name.replace('_', ' ').title()}",
            "model": f"{self.device_name}",
            "manufacturer": f"{self.manufacturer}",
        }
        for sensor in self.sensors:
            config = {
                "name": sensor['name'],
                "unique_id": f"{self.mac_address.replace(':','')}_{sensor['unique_id']}",
                "state_topic": sensor["state_topic"],
                "device": device_info,
            }
            # Add optional fields if present
            for key in ["unit_of_measurement", "icon", "state_class", "device_class"]:
                if key in sensor:
                    config[key] = sensor[key]
            await self.publish_home_assistant_discovery(
                "sensor", sensor["unique_id"], config
            )


# ----------------------- Fetch sensor data from database -------------------------

    def get_sensor_data(self, delay=30) -> Dict[str, Any]:
        """Query all sensors in one DB session with full retry."""
        while True:
            try:
                if not os.path.exists(self.db_path):
                    raise FileNotFoundError(f"DB file not found while fetching sensors: {self.db_path}")

                with open_db_snapshot(self.db_path) as conn:
                    cursor = conn.cursor()
                    data = {}
                    for sensor in self.sensors:
                        try:
                            data[sensor["unique_id"]] = sensor["query"](cursor)
                        except Exception as e:
                            self.logger.error(f"Error querying {sensor['unique_id']}: {e}")
                            data[sensor["unique_id"]] = None
                    return data  # success — return immediately
            except (sqlite3.OperationalError, FileNotFoundError) as e:
                self.logger.warning(f"DB access failed while fetching sensors, retrying in {delay}s: {e}")
                time.sleep(delay)

# ---------------------------- Sensor Loop -------------------------------

    async def publish_sensor_data(self, data: Dict[str, Any]):
        """Publish all sensor data to MQTT asynchronously"""
        for sensor in self.sensors:
            value = data.get(sensor["unique_id"])
            if value is not None:
                try:
                    await self.mqtt_client.publish(
                        sensor["state_topic"], str(value), qos=0, retain=True
                    )
                except Exception as e:
                    self.logger.error(f"Failed to publish {sensor['unique_id']}: {e}")
        self.logger.info(f"Published sensor data: {data}")

# --------------------------- Main Program -------------------------------

    async def run(self):
        """Main execution method (async, command-driven via MQTT)"""
        self.logger.info("Starting Gadgetbridge MQTT Publisher (command mode)")
        try:
            async with aiomqtt.Client(
                hostname=self.mqtt_config["broker"],
                port=self.mqtt_config["port"],
                username=self.mqtt_config["username"] or None,
                password=self.mqtt_config["password"] or None,
            ) as client:
                self.mqtt_client = client

                # Initialize HA entities
                await self.setup_home_assistant_entities()

                # Optional: publish once at startup
                sensor_data = self.get_sensor_data()
                command_topic = "gadgetbridge/command"
                await self.publish_sensor_data(sensor_data)
                self.logger.info(f"Published initial sensor data, waiting for payloads publish or ping on {command_topic}...")

                # Subscribe to command topic
                await client.subscribe(command_topic)

                #  Listen for incoming messages correctly
                async for message in client.messages:
                    payload = message.payload.decode().strip().lower()
                    self.logger.info(f"Received command on {message.topic}: {payload}")

                    try:
                        if payload in ("status", "publish", "go"):
                            sensor_data = self.get_sensor_data()
                            await self.publish_sensor_data(sensor_data)
                            self.logger.info("Published sensor data in response to command")

                        elif payload == "ping":
                            await client.publish("gadgetbridge/reply", "pong")
                            self.logger.info("Replied with pong")

                        else:
                            self.logger.warning(f"Unknown command: {payload}")

                    except Exception as e:
                        self.logger.error(f"Error handling command {payload}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")



# --- Main Entry Point ---
if __name__ == "__main__":
    publisher = GadgetbridgeMQTTPublisher()
    asyncio.run(publisher.run())
