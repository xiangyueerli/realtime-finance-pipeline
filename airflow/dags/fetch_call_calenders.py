from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.exceptions import AirflowSkipException
import pendulum
import pandas as pd


# Define the first DAG
with DAG(
    dag_id="fetch_call_calenders",

    # During DST (March–November)
    schedule="10 10,13,20,23 * * *",  # Run 4 times a day: 10:10 AM, 1:10 PM, 8:10 PM, and 11:10 PM UTC (6:10 AM, 9:10 AM, 4:10 PM, and 7:10 PM ET during DST)

    # During Standard Time (November–March)
    # schedule="10 11,14,21,0 * * *",  # Run 4 times a day: 11:10 AM, 2:10 PM, 9:10 PM, and 12:10 AM UTC (6:10 AM, 9:10 AM, 4:10 PM, and 7:10 PM ET during Standard Time)
    
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
        if calls_df is None or len(calls_df) == 0:
            raise AirflowSkipException("No calls data available for today, stopping the DAG.")
        
        # Convert the dictionary to a Pandas DataFrame
        calls_df = pd.DataFrame.from_dict(calls_df)
        
        # Determine the time slot dynamically based on execution time
        hour = execution_date.hour
        
        ### For testing purposes
        # hour = 20  # Set to 10 for pre-market, 20 for after-hours
        ### Testing purposes end
        

        if hour in [10,11,13,14]:  # Pre-market time slot
            time_slot = "pre_market"
            if 'time' in calls_df.columns:
                filtered_df = calls_df[
                    (calls_df['time'] == 'time-pre-market') | (calls_df['time'] == 'time-not-supplied')
                ]
            else:
                raise KeyError("The 'time' column is missing from the calls_df DataFrame.")

        elif hour in [20,21,23,0]:  # After-hours time slot
            time_slot = "after_hours"
            if 'time' in calls_df.columns:
                filtered_df = calls_df[
                    (calls_df['time'] == 'time-after-hours') | (calls_df['time'] == 'time-not-supplied')
                ]
            else:
                raise KeyError("The 'time' column is missing from the calls_df DataFrame.")

        else:
            raise ValueError("Unexpected execution time.")
        
        # Convert the DataFrame to a dictionary for XComs
        schedule_dict = filtered_df.to_dict()
        
        # Return the dictionary to XComs
        return {"time_slot": time_slot, "schedule_data": schedule_dict}
        

    
    # Push the schedule data to XComs
    schedule_data = fetch_schedule()
    
    # Trigger the second DAG dynamically
    trigger_second_dag = TriggerDagRunOperator(
        task_id="trigger_calls_firm_sentiment",
        trigger_dag_id="calls_firm_sentiment",  # Second DAG ID
        conf=schedule_data,  # Pass the schedule data to the second DAG
        wait_for_completion=False,
    )

    # Set task dependencies
    schedule_data >> trigger_second_dag

        
        