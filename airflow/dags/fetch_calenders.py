from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
import pendulum
import pandas as pd


# Define the first DAG
with DAG(
    dag_id="fetch_calenders",

    # During DST (Mar–Nov)
    schedule="0 10,20 * * *",  # Run twice a day: 10:00 AM UTC (pre-market) and 8:00 PM UTC (after-hours)
    # # During Standard Time (Nov–Mar)
    # schedule="0 11 * * *",  # 11:00 AM UTC = 6:00 AM EST
    
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    
) as dag:

    @task(task_id="fetch_schedule")
    def fetch_schedule(execution_date):
        from plugins.packages.FTRM.calls_calendars_layer import fetch_calls_calendars
        
        # Fetch the schedule data frame
        calls_df = fetch_calls_calendars()
        
        # Determine the time slot dynamically based on execution time
        hour = execution_date.hour
        if hour == 10:  # Pre-market time slot
            time_slot = "pre_market"
            filtered_df = calls_df[
                (calls_df['time'] == 'time-pre-market') & (calls_df['time'] == 'time-not-supplied')
            ]
        elif hour == 20:  # After-hours time slot
            time_slot = "after_hours"
            filtered_df = calls_df[
                (calls_df['time'] == 'time-after-hours') & (calls_df['time'] == 'time-not-supplied')
            ]

        
        print(f"Filtered DataFrame for {time_slot}: {filtered_df}")
        
        # Convert the DataFrame to a dictionary for XComs
        schedule_dict = filtered_df.to_dict()
        
        # Return the dictionary to XComs
        return {"time_slot": time_slot, "schedule_data": schedule_dict}
    
    # Push the schedule data to XComs
    schedule_data = fetch_schedule('{{ dag_run.logical_date }}')
    
    # Trigger the second DAG dynamically
    trigger_second_dag = TriggerDagRunOperator(
        task_id="trigger_calls_firm_sentiment",
        trigger_dag_id="calls_firm_sentiment",  # Second DAG ID
        conf=schedule_data,  # Pass the schedule data to the second DAG
        wait_for_completion=False,
    )

    # Set task dependencies
    schedule_data >> trigger_second_dag
        
        