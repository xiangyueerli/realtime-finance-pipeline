from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.exceptions import AirflowSkipException
import pendulum
import pandas as pd


# Define the first DAG
with DAG(
    dag_id="fetch_calenders",

    # During DST (Mar–Nov)
    schedule="0 10,20 * * *",  # Run twice a day: 10:00 AM UTC (6:00 AM EST, pre-market) and 8:00 PM UTC (4:00 PM EST, after-hours)
    # # During Standard Time (Nov–Mar)
    # schedule="0 11 * * *",  # 11:00 AM UTC = 6:00 AM EST
    
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    
) as dag:

    @task(task_id="fetch_schedule")
    def fetch_schedule(**kwargs):
        from plugins.packages.FTRM.calls_calendars_layer import fetch_calls_calendars
        
        # Access execution_date from kwargs
        execution_date = kwargs['execution_date']
        
        # Fetch the schedule data frame
        calls_df = fetch_calls_calendars()
        print(f"Fetched Calls DataFrame: {calls_df}")
        if calls_df is None or calls_df.empty:
            raise AirflowSkipException("No calls data available for today, stopping the DAG.")
        
        # Determine the time slot dynamically based on execution time
        hour = execution_date.hour
        
        # for testing purposes
        hour = 20  # Set to 10 for pre-market, 20 for after-hours

        if hour == 10:  # Pre-market time slot
            time_slot = "pre_market"
            filtered_df = calls_df[
                (calls_df['time'] == 'time-pre-market') | (calls_df['time'] == 'time-not-supplied')
            ]

        elif hour == 20:  # After-hours time slot
            time_slot = "after_hours"
            filtered_df = calls_df[
                (calls_df['time'] == 'time-after-hours') | (calls_df['time'] == 'time-not-supplied')
            ]

        # print(filtered_df.shape)
        # print(f"Filtered DataFrame for {time_slot}: {filtered_df}")
        
        # Convert the DataFrame to a dictionary for XComs
        schedule_dict = filtered_df.to_dict()
        
        # Return the dictionary to XComs
        return {"time_slot": time_slot, "schedule_data": schedule_dict}
    
    
    # # Example: Push Cron Expression in First DAG
    # @task(task_id="fetch_cron_expression")
    # def fetch_cron_expression(time_slot):
    #     schedule_map = {
    #         "pre_market": "*/5 11-13 * * *",
    #         "after_hours": "*/5 20-22 * * *",
    #     }
    #     # time_slot = "pre_market"  # Example: This could be dynamically determined
    #     cron_expression = schedule_map.get(time_slot, "*/5 11-13 * * *")
    #     print(f"Cron expression: {cron_expression}")
    #     return cron_expression
    
    # Push the schedule data to XComs
    schedule_data = fetch_schedule()
    # toss_cron_expression = fetch_cron_expression(schedule_data['time_slot'])
    
    # Trigger the second DAG dynamically
    trigger_second_dag = TriggerDagRunOperator(
        task_id="trigger_calls_firm_sentiment",
        trigger_dag_id="calls_firm_sentiment",  # Second DAG ID
        conf=schedule_data,  # Pass the schedule data to the second DAG
        wait_for_completion=False,
    )

    # Set task dependencies
    schedule_data >> trigger_second_dag

        
        