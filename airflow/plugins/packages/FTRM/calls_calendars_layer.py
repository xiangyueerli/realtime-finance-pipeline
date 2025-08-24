# # For the dockerised image
from datetime import datetime
from plugins.common.nasdaqAPI_finance_calendars import get_earnings_today
from plugins.common.hash_functions import generate_hash_id
import pandas as pd
from plugins.packages.FTRM.metadata import FileMetadata
from sqlalchemy.orm import Session
from airflow.exceptions import AirflowSkipException  # Import exception to stop DAG execution

def fetch_calls_calendars():
    calls = get_earnings_today()

    # No earnings today such as weekends or holidays
    if calls.empty or calls is None: 
        raise AirflowSkipException("No calls data available. Stopping DAG execution.")
    calls_df = calls[['time']]

    ### For testing purposes, let's create a mock DataFrame similar to expected output    

    # # Example output of calls_df will be
    #     symbol    time                             
    # AZZ      time-after-hours  
    # MEI      time-after-hours  
    # PCYO     time-after-hours  
    # THTX      time-pre-market  
    # BSET     time-after-hours  
    # ARTW    time-not-supplied  
    
    # mock_data = pd.DataFrame({
    #         "symbol": ["AZZ", "MEI", "PCYO", "THTX", "BSET", "ARTW"],
    #         "time": [
    #             "time-after-hours",
    #             "time-after-hours",
    #             "time-after-hours",
    #             "time-pre-market",
    #             "time-after-hours",
    #             "time-not-supplied"
    #         ]
    #     }).set_index("symbol")
    # print('Mock data created for testing purposes.')
    # print('Mock data:', mock_data)
    
    # return mock_data

    ### End of testing purposes

    #  Return the DataFrame as a dictionary (XComs can only store serializable data)
    return calls_df.to_dict()
    
    
    
    
    #####
    # earning_df.to_dict() will returns
    # {
    #     'time': {
    #         'DAL': 'time-not-supplied',
    #         'CAG': 'time-not-supplied',
    #         'LEVI': 'time-not-supplied',
    #         'VIST': 'pre_market',
    #         'PSMT': 'after-hours',
    #         'SMPL': 'pre_market',
    #         'WDFC': 'time-not-supplied',
    #         'ETWO': 'after_hours',
    #         'KALV': 'time-not-supplied'
    #     }
    # }
    
    # (In progress) Let's reorganise the data format later. First of all, input and output checking 
    #Example: Push Cron Expression in First DAG
    ####

def push_metadata(session, xcom_data, metadata_class):
    """
    Push the XCom data to the PostgreSQL meta data
    """
    for ticker, _ in xcom_data['schedule_data']['time'].items():
        download_date = datetime.now().date()
        # Generate a unique hash ID for the ticker
        hash_id = generate_hash_id(ticker, download_date)
        
        record = session.query(metadata_class).filter_by(ticker=ticker).first()
        if record:
            record.status = 'pending'
            record.download_date = datetime.datetime.now().date()
            record.is_deleted = False
        else:
            new_record = metadata_class(
                id = hash_id,
                ticker=ticker,
                download_date=datetime.datetime.now().date(),
                status='pending',
                is_deleted=False
            )
            session.add(new_record)
    
    return None

def check_if_data_downloaded(session, xcom_data, metadata_class):
    """
    Check if the data for the ticker is already downloaded from the meta data
    """
    tickers = list(xcom_data['schedule_data']['time'].keys())  # Extract the list of tickers from XCom data
    downloaded_tickers = session.query(metadata_class.ticker).filter(
        metadata_class.ticker.in_(tickers),  # Check if the ticker is in the provided list
        metadata_class.status == 'completed',  # Ensure the status is 'completed'
        metadata_class.is_deleted == False  # Ensure the record is not marked as deleted
    ).all()

    # Extract the tickers from the query result and return as a list
    return [ticker[0] for ticker in downloaded_tickers]


def update_list_of_firms(session, xcom_data, metadata_class):
    """
    Update the list of firms in the XCom data by removing already downloaded tickers.
    """
    downloaded_tickers = check_if_data_downloaded(session, xcom_data, metadata_class)
    xcom_data['schedule_data']['time'] = {
        ticker: time_slot
        for ticker, time_slot in xcom_data['schedule_data']['time'].items()
        if ticker not in downloaded_tickers
    }
    return None

def update_firm_status(session, ticker):
    """
    Update the status of a specific ticker in the metadata.
    """
    # To rigourously check if the current data is downloaded, we need an error layer to identify unsucessful downloads (e.g, empty contents, corrupted etc). 
    # If not error,
    record = session.query(FileMetadata).filter_by(ticker=ticker).first()
    if record:
        record.status = 'completed'
        record.is_deleted = False
        record.recent_update_date = datetime.datetime.now()
        print(f"Updated status for ticker: {ticker} to 'completed'")
        session.commit()
    else:
        print(f"No record found for ticker: {ticker}")
        
    # If error,
    # Leave a log.
    
    return None


# import os
# import sys
# from datetime import datetime
# from airflow.models import Variable
# # Temporarily modify sys.path to include the plugins directory for local testing
# sys.path.append('/data/seanchoi/airflow/plugins')
# for path in sys.path:
#     print(path)
    
# # Debugging: Print the current working directory
# print("Current Working Directory:", os.getcwd())

# # Debugging: Print the script's directory
# print("Script Directory:", os.path.dirname(os.path.abspath(__file__)))

# # Import the required modules
# try:
#     from common.nasdaqAPI_finance_calendars import get_earnings_today, get_earnings_by_date
#     print("Import successful!")
# except ModuleNotFoundError as e:
#     print("ModuleNotFoundError:", e)




# # # earning = get_earnings_today()
# earnings = get_earnings_by_date(datetime(2025, 7, 10, 0, 0))


# print(earnings['time'].unique())
# print(earnings[earnings['time'] == 'time-not-supplied'])
# print(earnings[earnings['time'] == 'after-hours'])
# print(earnings[earnings['time'] == 'pre-market'])

# # Define time slots and their corresponding schedules
# schedule_map = {
#     "pre_market": "*/5 11-13 * * *",  # Pre-market: Every 5 minutes from 11:00 AM to 2:00 PM UTC equivalent of 07:00 AM to 10:00 AM ET
#     "after_hours": "*/5 20-22 * * *",  # After-hours: Every 5 minutes from 8:00 PM to 11:00 PM UTC equivalent of 4:00 PM to 7:00 PM ET
# }

# # Fetch the current time slot from Airflow Variables
# time_slot = Variable.get("time_slot", default_var="pre_market")  # Default to pre-market

# # Get the dynamic schedule based on the time slot
# dynamic_schedule = schedule_map.get(time_slot, "*/5 11-13 * * *")  # Default to pre-market

