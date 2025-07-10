
import pendulum
from airflow import DAG
from airflow.decorators import task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.bash import BashOperator
from plugins.common.time_log_decorator import time_log
from db_utils import merge_ticker_quarter

import time
import os
import pandas as pd
import datetime



with DAG(
    dag_id="sec_pipeline",
    schedule="0 0 1 1,4,7,10 *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,

) as dag:
    
    ############################### Configurations ################################
    type = ['10-K', '10-Q']
    start_date = '2023-03-01'
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Save File Paths
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    # csv_file_path = os.path.join(base_path, "data/constituents/market/sp500_union_constituents.csv")
    csv_file_path = os.path.join(base_path, "data/constituents/market/test.csv")
    
    # Input Files
    data_raw_folder = os.path.join(base_path, "data/SP500/sec/market/html")
    extracted_folder = os.path.join(base_path, "data/SP500/sec/market/txt")


    ###############################################################################
    @task(task_id='t1_test')
    def test(PATH):
    
        df = pd.read_csv(PATH, encoding = 'utf-8')
        cik = df['CIK'].drop_duplicates().tolist() 
        
        return cik
    
    @task(task_id='t2_download_executor')
    @time_log
    def download_executor(firm_list_path, type, start_date, end_date, max_workers=os.cpu_count(), **kwargs):
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
        for t in type:
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
                print(123, "Futures created:", len(futures))

                error_flag = False
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error occurred: {e}")
                        error_flag = True

                if error_flag:
                    raise RuntimeError("Some downloads failed due to permission errors or other issues.")

    
    @task(task_id='t3_txt_convertor')
    @time_log
    def txt_convertor(data_folder, save_folder, **kwargs):
        from plugins.packages.FTRM.sec_txt_extractor import process_fillings_for_cik
        import concurrent.futures
        import os
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for cik in os.listdir(data_folder):
                future = executor.submit(process_fillings_for_cik, cik, data_folder, save_folder)
                futures.append(future)
                
                
            # Wait for all tasks to complete
            for future in futures:
                future.result()
            
            # All tasks are completed, shutdown the executor
            executor.shutdown()

    @task(task_id='t4_push_to_mongodb')
    def push_to_mongodb():
        """
        调用外部 push_quarterly_reports.py 中的 merge_ticker_quarter 函数
        将本地季度报告 txt 文件批量导入 MongoDB
        """
        # 将外部模块路径加入 Python 搜索路径
        try:
            merge_ticker_quarter()
            print("✅ Successfully pushed quarterly reports to MongoDB.")
        except Exception as e:
            raise RuntimeError("❌ Failed to push quarterly reports to MongoDB:", e)
    
    t2_download_executor = download_executor(csv_file_path, type = type, start_date=start_date, end_date=end_date)
    t3_txt_convertor = txt_convertor(data_raw_folder, extracted_folder)
    t4_push_to_mongodb = push_to_mongodb()
    
    t2_download_executor >> t3_txt_convertor >> t4_push_to_mongodb
