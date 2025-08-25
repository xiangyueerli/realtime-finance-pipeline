from airflow.sensors.base import BaseSensorOperator
from datetime import datetime
import pytz

class TimeRangeSensor(BaseSensorOperator):
    """
    A custom Airflow sensor to check if the current time is within a specified time range.
    """
    def __init__(self, task_id, Xcom, timezone="UTC", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.Xcom = Xcom
        self.timezone = pytz.timezone(timezone)

    def poke(self, context):
        # Fetch start_time and end_time from XCom dynamically
        start_time = self.Xcom['start_time']
        end_time = self.Xcom['end_time']

        # Ensure the values are datetime objects
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)

        # Get the current time in the specified timezone
        current_time = datetime.now(self.timezone)

        self.log.info(f"Current time: {current_time}, Start time: {start_time}, End time: {end_time}")
        return start_time <= current_time <= end_time