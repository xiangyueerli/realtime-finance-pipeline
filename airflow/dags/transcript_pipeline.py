
import pendulum
import os
import pandas as pd
import datetime
import logging
logger = logging.getLogger(__name__)

from db_utils import merge_transcripts
from airflow import DAG
from airflow.decorators import task
from plugins.common.time_log_decorator import time_log
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="calls_pipeline",
    schedule="0 0 1 1,4,7,10 *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,

) as dag:
    
    ############################### Configurations ################################

    start_date = '2023-05-01'
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Download Executor Configurations
    RATE_LIMIT = 5 # Maximum requests per second
    CONCURRENCY_LIMIT = 50 # the number of workers working concurrently
    BATCH_SIZE = 50 # Process 30 tickers at a time
    INITIAL_BACKOFF = 1 # Start with a 1-second delay
    MAX_RETRIES = 5 # Retry up to 5 times on failures
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    api_path = os.path.join(base_path, "api/ninjaapi_key.txt")
    with open(api_path, "r") as file:
        api_key = file.read().strip()
    
    # Save File Paths
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    final_save_path = os.path.join(base_path, "data/SP500/calls/market")
    csv_file_path = os.path.join(base_path, "data/constituents/market/test.csv")
    columns = ["Name", "CIK", "Date", "Body" ]
    firms_df = pd.read_csv(csv_file_path)
    columns_to_drop = ['Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Date added', 'Founded']
    firms_df = firms_df.drop(columns=columns_to_drop, errors='ignore')
    firms_df['CIK'] = firms_df['CIK'].apply(lambda x: str(x).zfill(10))
    cik = firms_df['CIK'].drop_duplicates().tolist()
    ticker = firms_df['Symbol'].tolist()
    cik_to_ticker = dict(zip(cik, ticker))
    
    # Input File    
    extracted_folder = os.path.join(base_path, "data/SP500/calls/market/json")


    ###############################################################################
    
    @task(task_id='t1_download_executor')
    @time_log
    def download_executor(save_folder, api_key, start_date, end_date, **kwargs):
        import asyncio
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').year
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').year
        
        async def async_download_executor():
            from plugins.packages.FTRM.extract_scripts_ninja import fetch_reports
            import aiohttp

            rate_limiter = asyncio.Semaphore(RATE_LIMIT)
            connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY_LIMIT)
            async with aiohttp.ClientSession(connector=connector) as session:
                tickers = list(cik_to_ticker.values())

                # Process in batches
                for i in range(0, len(tickers), BATCH_SIZE):
                    batch = tickers[i:i + BATCH_SIZE]
                    print(f"Processing batch {i // BATCH_SIZE + 1}: {batch}")
                    tasks = [fetch_reports(ticker, session, rate_limiter, save_folder, api_key, INITIAL_BACKOFF, MAX_RETRIES, year_until=end_date, year_since=start_date) for ticker in batch]
                    await asyncio.gather(*tasks)

        # Run the async function
        asyncio.run(async_download_executor())

        
    @task(task_id='t2_push_to_mongodb')
    def push_to_mongodb():
        try:
            merge_transcripts()
            logger.info("✅ Successfully pushed transcripts to MongoDB.")
        except Exception as e:
            raise RuntimeError(f"❌ Failed to push transcripts to MongoDB: {e}")
         
    
    #FTRM -> You should use correct API key to run this part. The current API is expired
    t1_download_executor = download_executor(save_folder=final_save_path, api_key=api_key, start_date=start_date, end_date=end_date)
    t2_push_to_mongodb = push_to_mongodb()

    
    t1_download_executor >> t2_push_to_mongodb 
        