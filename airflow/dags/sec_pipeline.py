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

Dependencies:
    - plugins.common.time_log_decorator
    - plugins.packages.FTRM.sec_crawler
    - plugins.packages.FTRM.sec_txt_extractor
    - plugins.packages.FTRM.html_pdf_convertor
"""

import os
import logging
logger = logging.getLogger(__name__)
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


with DAG(
    dag_id="sec_pipeline",
    schedule="0 0 1 1,4,7,10 *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
) as dag:
    
    ############################### Configurations ################################
    report_types = ['10-K', '10-Q']
    start_date = '2023-03-01'
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Save File Paths
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    # csv_file_path = os.path.join(base_path, "data/constituents/market/sp500_union_constituents.csv")
    csv_file_path = os.path.join(base_path, "data/constituents/market/test.csv")
    
    # Input Files
    data_raw_folder = os.path.join(base_path, "data/SP500/sec/market/html")
    extracted_folder = os.path.join(base_path, "data/SP500/sec/market/txt")
    pdf_folder = os.path.join(base_path, "data/SP500/sec/market/pdf")
    
    def copy_k10_json(src_dir, target_dir):
        json_file = "k10_list.json"
        src_file = os.path.join(src_dir, json_file)
        if os.path.exists(src_file):
            shutil.copy(src_file, target_dir)
            print(f"Copied {src_file} → {target_dir}")
        else:
            print(f"Source file not found: {src_file}")

    
    @task(task_id='t1_download_executor')
    @time_log
    def download_executor(firm_list_path, report_types, start_date, end_date, max_workers=os.cpu_count(), **kwargs):
        from plugins.packages.FTRM.sec_crawler import download_filing
        import os
        import pandas as pd
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        try:
            df = pd.read_csv(firm_list_path, encoding = 'utf-8')
            df_unique = df[['CIK', 'Symbol']].drop_duplicates() # 去重
            cik = df['CIK'].tolist()
            ticker = df['Symbol'].tolist()
            ciks_tickers = dict(zip(cik, ticker))
        except UnicodeDecodeError:
            df = pd.read_csv(firm_list_path, encoding = 'ISO-8859-1')
            # cik = df['CIK'].drop_duplicates().tolist()
            cik = df['CIK'].tolist()
            ticker = df['Symbol'].tolist()
            ciks_tickers = dict(zip(cik, ticker))
            
        # root_folder = '10k-html'
        for t in report_types:
            doc_type = t
            headers = {'User-Agent': 'University of Edinburgh s2101367@ed.ac.uk'}

            if not os.path.exists(data_raw_folder):
                os.makedirs(data_raw_folder)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for cik, ticker in ciks_tickers.items():
                    futures.append(
                        executor.submit(download_filing, cik, ticker, data_raw_folder, doc_type, headers, start_date, end_date)
                    )
                logger.info("Futures created:", len(futures))

                error_flag = False
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.info(f"Error occurred: {e}")           
                        error_flag = True

                if error_flag:
                    raise RuntimeError("Some downloads failed due to permission errors or other issues.")
                
        
    @task(task_id='t2_txt_convertor')
    @time_log
    def txt_convertor(data_folder, save_folder, **kwargs):
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for cik in os.listdir(data_folder):
                future = executor.submit(process_fillings_for_cik, cik, data_folder, save_folder)
                futures.append(future)

            # Wait for all tasks to complete
            for future in futures:
                future.result()
            
        # copy k10_list.json from /html to txt/
        copy_k10_json(data_raw_folder, extracted_folder)
            
    
    @task(task_id='t3_pdf_convertor')
    @time_log
    def pdf_convertor(data_folder, save_folder, **kwargs):
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for cik in os.listdir(data_raw_folder):
                # skip like k10_list.json
                if not cik.isdigit():
                    continue  
                future = executor.submit(process_fillings_html_to_pdf, cik, data_raw_folder, pdf_folder)
                futures.append(future)
                
            # Wait for all tasks to complete
            for future in futures:
                future.result()
        
        # copy k10_list.json from /html to pdf/
        copy_k10_json(data_raw_folder, pdf_folder)
            

    @task(task_id='t4_push_to_mongodb')
    def push_to_mongodb():
        """
        调用外部 push_quarterly_reports.py 中的 push_sec_reports 函数
        将本地 10-K/10-Q 报告 html,txt,pdf 文件或存储路径批量导入 MongoDB
        """
        # 将外部模块路径加入 Python 搜索路径
        try:
            push_sec_reports()
            logger.info("✅ Successfully pushed quarterly reports to MongoDB.")
        except Exception as e:
            raise RuntimeError(f"❌ Failed to push quarterly reports to MongoDB: {e}")
    
    t1_download_executor = download_executor(csv_file_path, report_types = report_types, start_date=start_date, end_date=end_date)
    t2_txt_convertor = txt_convertor(data_raw_folder, extracted_folder)
    t3_pdf_convertor = pdf_convertor(data_raw_folder, pdf_folder)
    
    t4_push_to_mongodb = push_to_mongodb()
    
    t1_download_executor >> t2_txt_convertor >> t3_pdf_convertor >> t4_push_to_mongodb
