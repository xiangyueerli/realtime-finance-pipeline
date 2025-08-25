from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.exceptions import AirflowSkipException
import pendulum
import pandas as pd


# Define the first DAG
with DAG(
    dag_id="fetch_sec_calenders",

    # During DST (March–November)
    schedule="0 10,13,20,23 * * *",  # Run 4 times a day: 10:00 AM, 1:00 PM, 8:00 PM, and 11:00 PM UTC (6:00 AM, 9:00 AM, 4:00 PM, and 7:00 PM ET during DST)

    # During Standard Time (November–March)
    # schedule="0 11,14,21,0 * * *",  # Run 4 times a day: 11:00 AM, 2:00 PM, 9:00 PM, and 12:00 AM UTC (6:00 AM, 9:00 AM, 4:00 PM, and 7:00 PM ET during Standard Time)
    
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    
) as dag:

    @task(task_id="fetch_schedule")
    def fetch_schedule(sec_calenders_estimates, **kwargs):
        from plugins.packages.FTRM.sec_calendars_layer import SECCalendar
        
        # Access execution_date from kwargs
        execution_date = kwargs['execution_date']
        
        sec_calender = SECCalendar(folder_path_10q=None, folder_path_10k=None)
        # Fetch the SEC calendar data
        sec_tody_list = sec_calender.fetch_sec_daily_calendars(sec_calenders_estimates)

        print(f"Fetched Calls DataFrame: {sec_tody_list}")
        if sec_tody_list is None or len(sec_tody_list) == 0:
            raise AirflowSkipException("No calls data available for today, stopping the DAG.")
    
        # Determine the time slot dynamically based on execution time
        hour = execution_date.hour
        
        if hour == 10:  # Pre-market time slot
            time_slot = "pre_market"

        elif hour == 20:  # After-hours time slot
            time_slot = "after_hours"
    
        sec_today_df = pd.DataFrame(sec_tody_list, columns=['todayTargets'])  # Convert list to DataFrame
        # sec_today_df's example: {'todayTargets': {0: '0000001800', 1: '000620948', 2: 'xxxxxxxxxx', 3: 'xxxxxxxxxx', erc...}}
        
        # Convert the DataFrame to a dictionary for XComs
        schedule_dict = sec_today_df.to_dict()
        
        
        # Return the dictionary to XComs
        return {"time_slot": time_slot, "schedule_data": schedule_dict}
    
    sec_calenders_estimates = "/data/seanchoi/airflow/data/calenders/sec_predicted_calendar_output.json"
    # Push the schedule data to XComs
    schedule_data = fetch_schedule(sec_calenders_estimates)
    # toss_cron_expression = fetch_cron_expression(schedule_data['time_slot'])
    
    # Trigger the second DAG dynamically
    trigger_second_dag = TriggerDagRunOperator(
        task_id="trigger_sec_firm_sentiment",
        trigger_dag_id="sec_firm_sentiment",  # Second DAG ID
        conf=schedule_data,  # Pass the schedule data to the second DAG
        wait_for_completion=False,
    )

    # Set task dependencies
    schedule_data >> trigger_second_dag

        
        