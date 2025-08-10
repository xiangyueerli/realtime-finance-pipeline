"""
Airflow DAG: calls_pipeline

Author: Chunyu Yan
Date: 2025-07-29
Description:
    This DAG automates the quarterly pipeline to fetch earnings call transcripts
    using the Ninja API and uploads the parsed content to MongoDB. The process includes:

    1. Downloading call transcripts for S&P 500 companies via Ninja API
    2. Saving raw JSONs to local folders
    3. Parsing and structuring transcript data
    4. Uploading structured data (with company, date, CIK) to MongoDB

    Execution Frequency:
        - Scheduled quarterly (Jan 1, Apr 1, Jul 1, Oct 1)

    Notes:
        - You must use a valid API key for Ninja API.
        - JSON files are saved under $AIRFLOW_HOME/data/SP500/calls/market/json
        - MongoDB stores the final transcript records.
"""

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


with DAG(
    dag_id="calls_pipeline",
    schedule="0 0 1 1,4,7,10 *",  # Quarterly
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
) as dag:
    
    ################################## Config ##################################

    start_date = '2024-01-01'
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # API and concurrency settings
    RATE_LIMIT = 5               # Max requests per second
    CONCURRENCY_LIMIT = 50       # Max concurrent aiohttp connections
    BATCH_SIZE = 50              # Number of tickers processed in one batch
    INITIAL_BACKOFF = 1          # Initial retry delay in seconds
    MAX_RETRIES = 5              # Max retry attempts per request

    # Paths
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    api_path = os.path.join(base_path, "api/ninjaapi_key.txt")
    with open(api_path, "r") as file:
        api_key = file.read().strip()

    final_save_path = os.path.join(base_path, "data/SP500/calls/market")
    extracted_folder = os.path.join(final_save_path, "json")
    csv_file_path = os.path.join(base_path, "data/constituents/market/test.csv")

    # Read firm metadata
    columns = ["Name", "CIK", "Date", "Body"]
    firms_df = pd.read_csv(csv_file_path)
    columns_to_drop = ['Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Date added', 'Founded']
    firms_df = firms_df.drop(columns=columns_to_drop, errors='ignore')
    firms_df['CIK'] = firms_df['CIK'].apply(lambda x: str(x).zfill(10))
    cik = firms_df['CIK'].drop_duplicates().tolist()
    ticker = firms_df['Symbol'].tolist()
    cik_to_ticker = dict(zip(cik, ticker))


    @task(task_id='t1_download_executor')
    @time_log
    def download_executor(save_folder, api_key, start_date, end_date, **kwargs):
        """
        Download earnings call transcripts using the Ninja API via asyncio + aiohttp.

        - Requests are throttled using semaphores.
        - Batch download is performed per 50 tickers.
        - JSON files are stored locally for later parsing.
        """
        import asyncio
        start_year = datetime.datetime.strptime(start_date, '%Y-%m-%d').year
        end_year = datetime.datetime.strptime(end_date, '%Y-%m-%d').year

        async def async_download_executor():
            from plugins.packages.FTRM.extract_scripts_ninja import fetch_reports
            import aiohttp

            rate_limiter = asyncio.Semaphore(RATE_LIMIT)
            connector = aiohttp.TCPConnector(limit_per_host=CONCURRENCY_LIMIT)
            async with aiohttp.ClientSession(connector=connector) as session:
                tickers = list(cik_to_ticker.values())
                for i in range(0, len(tickers), BATCH_SIZE):
                    batch = tickers[i:i + BATCH_SIZE]
                    print(f"Processing batch {i // BATCH_SIZE + 1}: {batch}")
                    tasks = [
                        fetch_reports(
                            ticker,
                            session,
                            rate_limiter,
                            save_folder,
                            api_key,
                            INITIAL_BACKOFF,
                            MAX_RETRIES,
                            year_until=end_year,
                            year_since=start_year
                        )
                        for ticker in batch
                    ]
                    await asyncio.gather(*tasks)

        asyncio.run(async_download_executor())

        
    @task(task_id='t2_push_to_mongodb')
    def push_to_mongodb():
        """
        Parse local transcript JSONs and upload structured documents to MongoDB.
        """
        try:
            merge_transcripts()
            logger.info("✅ Successfully pushed transcripts to MongoDB.")
        except Exception as e:
            raise RuntimeError(f"❌ Failed to push transcripts to MongoDB: {e}")

    
    t1_download_executor = download_executor(
        save_folder=final_save_path,
        api_key=api_key,
        start_date=start_date,
        end_date=end_date
    )
    t2_push_to_mongodb = push_to_mongodb()

    t1_download_executor >> t2_push_to_mongodb
