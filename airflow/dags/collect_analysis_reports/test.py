from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

# # Default arguments for the DAG
# default_args = {
#     'owner': 'airflow',  # Owner of the task
#     'depends_on_past': False,  # Ignore previous task failures
#     'email': ['example@example.com'],  # Email notifications
#     'email_on_failure': False,
#     'email_on_retry': False,
#     'retries': 1,  # Retry count
#     'retry_delay': timedelta(minutes=5),  # Retry interval
# }

# Define the DAG
dag = DAG(
    'test',  # Name of the DAG
    description='A simple example DAG',  # Description
    schedule_interval=timedelta(days=1),  # Schedule interval
    start_date=datetime(2025, 1, 1),  # Start date
    catchup=False,  # Skip tasks for backfilled dates
)

# Define tasks
start = DummyOperator(
    task_id='start',  # Task ID
    dag=dag,
)

def print_hello():
    print("Hello, World!")

task_1 = PythonOperator(
    task_id='print_hello',
    python_callable=print_hello,  # Function to execute
    dag=dag,
)

end = DummyOperator(
    task_id='end',
    dag=dag,
)

# Define task dependencies
start >> task_1 >> end
