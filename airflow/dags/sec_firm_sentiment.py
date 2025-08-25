
import pendulum
from airflow import DAG
from airflow.decorators import task
from plugins.common.time_log_decorator import time_log
from plugins.common.sensors.time_range_sensor import TimeRangeSensor
import time
import os
import pandas as pd
import datetime
from datetime import date, datetime
from airflow.models.xcom_arg import XComArg

with DAG(
    dag_id="sec_firm_sentiment",
    schedule="0 0 1 1,4,7,10 *",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,

) as dag:
    
    ############################### Configurations ################################
    start_date = '2025-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Save File Paths
    base_path = os.getenv("AIRFLOW_HOME", "/opt/airflow")
    final_save_path = os.path.join(base_path, "data/SP500/sec/firm")
    csv_file_path = os.path.join(base_path, "data/constituents/market/sp500_union_constituents.csv")

    
    # Input Files
    data_raw_folder = os.path.join(base_path, "data/SP500/sec/firm/html")
    extracted_folder = os.path.join(base_path, "data/SP500/sec/firm/txt")


    ###############################################################################
    @task(task_id='t1_test')
    def test(PATH):
    
        df = pd.read_csv(PATH, encoding = 'utf-8')
        cik = df['CIK'].drop_duplicates().tolist() 
        
        return cik
    
    @task(task_id='t1_process_schedule_data')
    def process_schedule_data(csv_file_path=csv_file_path, **kwargs):
        conf = kwargs.get('dag_run').conf
        time_slot = conf.get('time_slot', 'pre_market')  # Default to pre-market if not provided
        schedule_data = conf.get('schedule_data', {})
        
        print('schedule_data:', schedule_data)
        if not schedule_data:
            raise ValueError("No schedule data found in the DAG run configuration.")
        
        # Process the schedule data and extract CIKs
        firms_df = pd.read_csv(csv_file_path)
        columns_to_drop = ['Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location', 'Date added', 'Founded']
        firms_df = firms_df.drop(columns=columns_to_drop, errors='ignore')
        firms_df['CIK'] = firms_df['CIK'].apply(lambda x: str(x).zfill(10))
            
        # Extract the 'todayTargets' from the schedule data
        today_targets = list(schedule_data.get('todayTargets', {}).values())
        firms_df = firms_df[firms_df['CIK'].isin(today_targets)]
        cik = firms_df['CIK'].drop_duplicates().tolist()
        ticker = firms_df['Symbol'].tolist()
        cik_ticker = dict(zip(cik, ticker))
        print('cik_ticker:', cik_ticker)

        return {'time_slot': time_slot, 'cik_ticker': cik_ticker}
    
    def connect_2_postgres():

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        db_url = "postgresql://metadata:metadata@metadata_postgres_container:5432/ftrm"
        engine = create_engine(db_url, pool_size=10, max_overflow=5, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal()
    
    @task(task_id='t2_download_executor')
    def execute_dynamic_logic(Xcom, save_folder, start_date, end_date, **kwargs):

        from plugins.packages.FTRM.sec_calendars_layer import SECCalendar
        from plugins.packages.FTRM.metadata import SECMetadata

        sec_calender = SECCalendar(folder_path_10q=None, folder_path_10k=None)

        type = filing_type(today=None)  
        try:
            # Need to implement interface by data type 
            # Database connection
            session = connect_2_postgres()
            # Push the Xcom to the PostgreSQL meta data
            sec_calender.push_metadata(
                session = session, 
                xcom_data = Xcom,
                type = type,
                metadata_class = SECMetadata
            )  # Specify the metadata class to use
            
            # Check if a firm's data is alreadly donwloaded from a meta data
            # If yes, remove it from the list of firms to process. If not, keep it in the list
            sec_calender.update_list_of_firms(
                session = session,
                xcom_data = Xcom,
                metadata_class= SECMetadata
            )  # Specify the metadata class to use
            
            time_slot = Xcom['time_slot']  # Extract time_slot from the dictionary
            cik_ticker = Xcom['cik_ticker']  # Extract schedule_data from the dictionary
            
            download_executor(cik_ticker, save_folder, type, start_date, end_date, **kwargs)

            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"An error occurred: {e}")
        finally:
            # Close the session to release resources
            session.close()
    

    def filing_type(today=None):
        if today is None:
            today = date.today()

        month = today.month

        if month in [1, 2, 3]:      # Q1
            return "10-Q"
        elif month in [4, 5, 6]:    # Q2
            return "10-Q"
        elif month in [7, 8, 9]:    # Q3
            return "10-Q"
        else:                       # Q4 (Oct–Dec)
            return "10-K"
        
    
    @time_log
    def download_executor(cik_tickers, save_folder, type, start_date, end_date, **kwargs):
        from plugins.packages.FTRM.sec_crawler import download_filing
        from plugins.packages.FTRM.sec_calendars_layer import SECCalendar
        from plugins.packages.FTRM.metadata import SECMetadata
        import os
        import pandas as pd
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        max_workers = os.cpu_count()  # Use all available CPU cores

        headers = {'User-Agent': 'University of Edinburgh schoi3@ed.ac.uk'} # User Emails

        if not os.path.exists(save_folder):
            os.makedirs(save_folder)
        # The `download_fillings` function is a custom function imported from the
        # `plugins.packages.FTRM.sec_crawler` module. This function is used to download filings
        # for a list of companies based on their CIK (Central Index Key) and ticker symbols. The
        # function takes parameters such as the dictionary mapping CIK to ticker symbols, the data
        # folder path where the filings will be saved, the type of document to download (e.g.,
        # '10-K' or '10-Q'), headers for the HTTP request, start date, and end date for the
        # filings to be downloaded.
        
        session = connect_2_postgres()
        
        sec_calendar = SECCalendar(folder_path_10q=None, folder_path_10k=None)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for cik, ticker in cik_tickers.items():
                futures.append(
                    executor.submit(download_filing, cik, ticker, save_folder, type, headers, start_date, end_date)
                )
                print('future', futures)
                print(f"Submitting task for CIK: {cik}, Ticker: {ticker}")

            for future, (cik, ticker) in zip(as_completed(futures), cik_tickers.items()):
                try:
                    # Check if the download was successful
                    future.result()  # Raise exceptions if any occurred during execution
                    sec_calendar.update_firm_status(
                        session = session,
                        ticker = ticker,
                        metadata_class = SECMetadata,
                        success=True
                        )  # Mark as completed
                except Exception as e:
                    print(f"Error occurred while downloading for ticker {ticker}: {e}")
                    sec_calendar.update_firm_status(
                        session = session,
                        ticker = ticker,
                        metadata_class = SECMetadata,
                        success=False
                        )  # Mark as failed

        # Close the session
        session.close()
    
    # Define the time range dynamically based on the time slot
    def get_time_range(time_slot):
        if time_slot == "pre_market":
            start_time = datetime.now().replace(hour=11, minute=0, second=0, microsecond=0)
            end_time = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
        elif time_slot == "after_hours":
            start_time = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)
            end_time = datetime.now().replace(hour=22, minute=0, second=0, microsecond=0)
        else:
            raise ValueError("Unknown time slot")
        return start_time, end_time
    
    @task(task_id='t3_txt_convertor')
    @time_log
    def txt_convertor(data_folder, save_folder, **kwargs):
        from plugins.packages.FTRM.sec_txt_extractor import process_fillings_for_cik
        import concurrent.futures
        import os
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for cik in os.listdir(data_folder):
                # Skip the file, only process directories
                if not os.path.isdir(root_folder):
                    continue 
                future = executor.submit(process_fillings_for_cik, cik, data_folder, save_folder)
                futures.append(future)
                
                
            # Wait for all tasks to complete
            for future in futures:
                future.result()
            
            # All tasks are completed, shutdown the executor
            executor.shutdown()

        
    @task(task_id='t4_dtm_constructor')
    @time_log
    def dtm_constructor(data_folder, save_folder, csv_file_path, columns, start_date, end_date, **kwargs):
        import os
        from plugins.packages.PDCM.constructDTM import ConstructDTM
        from pyspark.sql import SparkSession
        import subprocess
        # Optional: Check if Java is visible
        subprocess.run(["java", "-version"], check=True)
                
                
        os.environ['PYSPARK_SUBMIT_ARGS'] = "--master local[2] pyspark-shell"

        # Initialize Spark session
        spark = (
            SparkSession.builder
            .appName("DataPipeline")
            .master("local[2]")
            # Memory allocations
            .config("spark.driver.memory", "6g")
            .config("spark.executor.memory", "6g")
            .config("spark.sql.shuffle.partitions", "4") 
            .getOrCreate()
        )
        pipeline = ConstructDTM(spark, data_folder, save_folder, csv_file_path, columns, start_date, end_date)
        pipeline.file_aggregator()
        pipeline.process_filings_for_cik_spark(save_folder, start_date, end_date, csv_file_path)
        constituents_metadata_path = os.path.join(base_path, "data/constituents/market/sp500_constituents.csv") # This is for getting the CIKs for the SP500, but only for the year 2006 - 2023
        pipeline.concatenate_parquet_files(final_save_path, csv_file_path, constituents_metadata_path, start_date, end_date)
        
    @task(task_id='t5_sent_predictor')
    @time_log
    def sent_predictor(window, **kwargs):
        from plugins.packages.SSPM.sent_predictor_firm import SentimentPredictor
        config = {
            "constituents_path": os.path.join(os.getenv("AIRFLOW_HOME", "/opt/airflow"), f'{csv_file_path}'),
            "fig_loc": os.path.join(os.getenv("AIRFLOW_HOME", "/opt/airflow"), "data/SP500/sec/firm/outcome/figures"),
            "input_path": os.path.join(os.getenv("AIRFLOW_HOME", "/opt/airflow"), "data/SP500/sec/firm/processed/dtm_0001045810.parquet"),
            "window": window,
            }
        predictor = SentimentPredictor(config)
        predictor.run()
    
    # FTRM
    t1_process_schedule_data = process_schedule_data(csv_file_path=csv_file_path)  # Process the schedule data and extract CIKs
    
    t2_download_executor = execute_dynamic_logic(t1_process_schedule_data, save_folder=data_raw_folder ,start_date=start_date, end_date=end_date)  # Execute the dynamic logic based on the time slot
        
    t3_txt_convertor = txt_convertor(data_raw_folder, extracted_folder)
    # PDCM
    t4_dtm_constructor = dtm_constructor(extracted_folder, final_save_path, t1_process_schedule_data, ["Name", "CIK", "Date", "Body" ], start_date, end_date)

    # SSPM
    t5_sent_predictor = sent_predictor(window=end_date)

    
    t1_process_schedule_data >> t2_download_executor >> t3_txt_convertor >> t4_dtm_constructor >> t5_sent_predictor

        