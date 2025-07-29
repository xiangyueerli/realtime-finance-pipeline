"""
Airflow DAG: sec_pipeline

Author: Chunyu Yan
Date: 2025-07-29
Description:
    This DAG automates the quarterly ingestion of SEC 10-K and 10-Q filings
    for S&P 500 companies. The process includes:

    1. Downloading filings via the EDGAR API (parallelized by CIK)
    2. Extracting txt content from HTML documents
    3. Converting HTML to PDF format for analyst use
    4. Uploading structured data (text, HTML, PDF paths) to MongoDB

    Execution Frequency:
        - Scheduled quarterly (Jan 1, Apr 1, Jul 1, Oct 1)

    Notes:
        - The task is designed for batch processing over firm lists
        - Filings are stored under $AIRFLOW_HOME/data/SP500/sec/market/
        - MongoDB is used as a centralized structured backend
"""

import os
import logging
import pendulum
import concurrent.futures
import pandas as pd
import datetime
import shutil

from airflow import DAG
from airflow.decorators import task
from plugins.common.time_log_decorator import time_log
from db_utils import push_sec_reports
from plugins.packages.FTRM.sec_txt_extractor import process_fillings_for_cik
from plugins.packages.FTRM.html_pdf_convertor import process_fillings_html_to_pdf

logger = logging.getLogger(__name__)


with DAG(
    dag_id="sec_pipeline",
    schedule="0 0 1 1,4,7,10 *",  # Quarterly on Jan 1, Apr 1, Jul 1, Oct 1
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
) as dag:
    
    ################################## Config ##################################
    report_types = ['10-K', '10-Q']
    start_date = '2023-03-01'
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    csv_file_path = os.path.join(base_path, "data/constituents/market/test.csv")
    
    data_raw_folder = os.path.join(base_path, "data/SP500/sec/market/html")
    extracted_folder = os.path.join(base_path, "data/SP500/sec/market/txt")
    pdf_folder = os.path.join(base_path, "data/SP500/sec/market/pdf")

    def copy_k10_json(src_dir, target_dir):
        """
        Copy k10_list.json file from source to target directory if it exists.
        """
        json_file = "k10_list.json"
        src_file = os.path.join(src_dir, json_file)
        if os.path.exists(src_file):
            target_file = os.path.join(target_dir, json_file)
            shutil.copyfile(src_file, target_file)
            print(f"Copied {src_file} → {target_file}")
        else:
            print(f"Source file not found: {src_file}")

    
    @task(task_id='t1_download_executor')
    @time_log
    def download_executor(firm_list_path, report_types, start_date, end_date, max_workers=os.cpu_count(), **kwargs):
        """
        Download 10-K and 10-Q filings from EDGAR API using multithreading.

        Each CIK/ticker is processed in parallel using ThreadPoolExecutor.
        """
        from plugins.packages.FTRM.sec_crawler import download_filing
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        try:
            df = pd.read_csv(firm_list_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(firm_list_path, encoding='ISO-8859-1')

        df_unique = df[['CIK', 'Symbol']].drop_duplicates()
        cik = df_unique['CIK'].tolist()
        ticker = df_unique['Symbol'].tolist()
        ciks_tickers = dict(zip(cik, ticker))

        for doc_type in report_types:
            headers = {'User-Agent': 'University of Edinburgh s2101367@ed.ac.uk'}
            os.makedirs(data_raw_folder, exist_ok=True)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(download_filing, cik, ticker, data_raw_folder, doc_type, headers, start_date, end_date)
                    for cik, ticker in ciks_tickers.items()
                ]

                logger.info("Created futures: %d", len(futures))
                error_flag = False

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Download error: {e}")
                        error_flag = True

                if error_flag:
                    raise RuntimeError("Some downloads failed due to permission errors or other issues.")

    
    @task(task_id='t2_txt_convertor')
    @time_log
    def txt_convertor(data_folder, save_folder, **kwargs):
        """
        Convert HTML filings to plain text (.txt) using multithreading.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [
                executor.submit(process_fillings_for_cik, cik, data_folder, save_folder)
                for cik in os.listdir(data_folder)
            ]
            for future in futures:
                future.result()
        
        copy_k10_json(data_raw_folder, extracted_folder)
            

    @task(task_id='t3_pdf_convertor')
    @time_log
    def pdf_convertor(data_folder, save_folder, **kwargs):
        """
        Convert HTML filings to PDF using multithreading.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for cik in os.listdir(data_raw_folder):
                if not cik.isdigit():
                    continue  # Skip non-CIK files like k10_list.json
                futures.append(executor.submit(process_fillings_html_to_pdf, cik, data_raw_folder, pdf_folder))

            for future in futures:
                future.result()

        copy_k10_json(data_raw_folder, pdf_folder)


    @task(task_id='t4_push_to_mongodb')
    def push_to_mongodb():
        """
        Upload extracted report metadata (HTML, TXT, PDF paths) to MongoDB.
        """
        try:
            push_sec_reports()
            logger.info("✅ Successfully pushed quarterly reports to MongoDB.")
        except Exception as e:
            raise RuntimeError(f"❌ Failed to push quarterly reports to MongoDB: {e}")
    

    # Task dependency setup
    t1 = download_executor(csv_file_path, report_types=report_types, start_date=start_date, end_date=end_date)
    t2 = txt_convertor(data_raw_folder, extracted_folder)
    t3 = pdf_convertor(data_raw_folder, pdf_folder)
    t4 = push_to_mongodb()

    t1 >> t2 >> t3 >> t4
