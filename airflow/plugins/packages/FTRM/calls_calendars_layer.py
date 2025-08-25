
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

    return calls_df.to_dict()
    

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
            record.download_date = datetime.now().date()
            record.is_deleted = False
        else:
            new_record = metadata_class(
                id = hash_id,
                ticker=ticker,
                download_date=datetime.now().date(),
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

