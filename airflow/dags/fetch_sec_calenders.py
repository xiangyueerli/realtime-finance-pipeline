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

    # During DST (Mar–Nov)
    schedule="0 11,21 * * *",  # Run twice a day: 11:00 AM UTC (7:00 AM EST, pre-market) and 9:00 PM UTC (5:00 PM EST, after-hours)
    # # During Standard Time (Nov–Mar)
    # schedule="0 11 * * *",  # 12:00 AM UTC = 7:00 AM EST
    
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    
) as dag:

    @task(task_id="fetch_schedule")
    def fetch_schedule(**kwargs):
        from plugins.packages.FTRM.sec_calendars_layer import fetch_sec_daily_calendars
        
        # Fetch the SEC calendar data
        sec_tody_list = fetch_sec_daily_calendars()
        # Fetch the schedule data frame
        # calls_df = fetch_calls_calendars()
        print(f"Fetched Calls DataFrame: {sec_tody_list}")
        if sec_tody_list is None or sec_tody_list.empty:
            raise AirflowSkipException("No calls data available for today, stopping the DAG.")
    
        sec_today_df = pd.DataFrame(sec_tody_list, columns=['todayTargets'])  # Convert list to DataFrame
        # sec_today_df = {'todayTargets': {0: '0000001800', 1: '000620948', 2: 'xxxxxxxxxx', 3: 'xxxxxxxxxx', erc...}}
        # Convert the DataFrame to a dictionary for XComs
        schedule_dict = sec_today_df.to_dict()
        
        # Return the dictionary to XComs
        return {"schedule_data": schedule_dict}
    

    # Push the schedule data to XComs
    schedule_data = fetch_schedule()
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

        
        