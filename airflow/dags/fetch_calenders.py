from airflow import DAG
from airflow.decorators import task

import pendulum
import pandas as pd


# Define the first DAG
with DAG(
    dag_id="fetch_calenders",

    # During DST (Mar–Nov)
    schedule="0 10 * * *",  # 10:00 AM UTC = 6:00 AM EDT
    # # During Standard Time (Nov–Mar)
    # schedule="0 11 * * *",  # 11:00 AM UTC = 6:00 AM EST
    
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    
) as dag:

    @task(task_id="fetch_schedule")
    def fetch_schedule():
        from plugins.packages.FTRM.calls_calendars_layer import fetch_calls_calendars
        
        # Fetch the schedule data frame
        calls_dict = fetch_calls_calendars()
        return calls_dict
    
    # Push the schedule data to XComs
    schedule_data = fetch_schedule()
        
        