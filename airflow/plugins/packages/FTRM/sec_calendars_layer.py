import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from collections import defaultdict
from itertools import islice
from plugins.packages.FTRM.metadata import FileMetadata
import json
from datetime import datetime


class SECCalender:
    def __init__(self, folder_path_10q, folder_path_10k):
        self.folder_path_10q = folder_path_10q
        self.folder_path_10k = folder_path_10k

    def list_files_in_folder(self, folder_path):
        try:
            return [
                os.path.splitext(file_name)[0]  # Remove the '.html' extension
                for file_name in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, file_name))
            ]
        except FileNotFoundError:
            print(f"The folder '{folder_path}' does not exist.")
            return []
        
    def get_firm_paths_dict(self, folder_path):
        """Get a list of full paths for all folders in the specified directory."""
        cik_2_paths = defaultdict(list)
        try:
            for folder_name in os.listdir(folder_path):
                if os.path.isdir(os.path.join(folder_path, folder_name)):
                    cik_2_paths[folder_name].append(os.path.join(folder_path, folder_name))
            return cik_2_paths
        except FileNotFoundError:
            print(f"The folder '{folder_path}' does not exist.")
            return defaultdict(list)
                    
        
        # try:
        #     return [
        #         os.path.join(folder_path, folder_name)
        #         for folder_name in os.listdir(folder_path)
        #         if os.path.isdir(os.path.join(folder_path, folder_name))
        #     ]
        # except FileNotFoundError:
        #     print(f"The folder '{folder_path}' does not exist.")
        #     return []


    def get_sec_release_dates(self, firm_path_dict_10q, firm_path_dict_10k):
        '''
        Get the release dates for each firm from the 10-Q and 10-K filings.
        Output: 
            '0001116132': ['2018-05-09', '2025-02-06', ...], 
            '0001478242': ['2018-02-16', '2014-02-13','...] ...
        '''
        
        firm_path_dict = self.combine_dicts(firm_path_dict_10q, firm_path_dict_10k) # key: CIK, value: list of paths        
        firm_2_dates = defaultdict(list)

        for cik, firm_paths in firm_path_dict.items():
        
            date_10q = []
            date_10k = []
            
            if len(firm_paths) > 0:
                dates_10q = self.list_files_in_folder(firm_paths[0])  # Assuming the first path is for 10-Q
            if len(firm_paths) > 1:
                dates_10k = self.list_files_in_folder(firm_paths[1])  # Assuming the second path is for 10-K
            firm_dates = dates_10q + dates_10k
            firm_2_dates[cik] = firm_dates
            
        
        return firm_2_dates
    
    def combine_dicts(self, dict1, dict2):
        """Combine two dictionaries by merging values for keys that are the same."""
        combined_dict = {}

        # Add all keys from dict1
        for key, value in dict1.items():
            if key in dict2:
                # Combine values if the key exists in both dictionaries
                combined_dict[key] = value + dict2[key]
            else:
                # Add value from dict1 if the key is not in dict2
                combined_dict[key] = value

        # Add remaining keys from dict2 that are not in dict1
        for key, value in dict2.items():
            if key not in combined_dict:
                combined_dict[key] = value

        return combined_dict


    def predict_focus_windows(self, cik, dates, window_days=5):        
        # dates_list = dates.tolist() 
        """ Predict optimal collection windows for each quarter with a small window (~3 days). """
        dates = pd.to_datetime(dates)
        df = pd.DataFrame({"date": dates})
        df["quarter"] = df["date"].dt.month.apply(self.get_quarter)
        df["day_of_year"] = df["date"].dt.dayofyear

        quarter_windows = {}

        for quarter, group in df.groupby("quarter"):
            median_day = int(group["day_of_year"].median())
            start_day = median_day - window_days // 2
            end_day = median_day + window_days // 2

            base_year = 2025 # this is arbitrary, just to create a date
            start_date = pd.Timestamp(base_year, 1, 1) + pd.Timedelta(days=start_day - 1)
            end_date = pd.Timestamp(base_year, 1, 1) + pd.Timedelta(days=end_day - 1)

            quarter_windows[quarter] = (start_date.strftime("%b-%d"), end_date.strftime("%b-%d"))

        return quarter_windows

    def get_quarter(self, month):
        """Determine the quarter of the year based on the month."""
        if 1 <= month <= 3:
            return 1
        elif 4 <= month <= 6:
            return 2
        elif 7 <= month <= 9:
            return 3
        elif 10 <= month <= 12:
            return 4
        else:
            raise ValueError("Invalid month value")
        
    def fetch_sec_daily_calendars(self, json_file_path):
        """
        Get a list of CIKs where today's date overlaps with their quarter windows.
        
        Args:
            json_file_path (str): Path to the JSON file containing quarter windows data.
        
        Returns:
            list: List of CIKs with overlapping dates.
        """
        # Load the JSON data
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Get today's date in the format 'MMM-DD' (e.g., 'Feb-22')
        today = datetime.now().strftime('%b-%d')
        
        # Find CIKs with overlapping dates
        overlapping_ciks = []
        for cik, quarters in data.items():
            for quarter, dates in quarters.items():
                if today in dates:
                    overlapping_ciks.append(cik)
                    break  # No need to check further quarters for this CIK
        
        return overlapping_ciks
    
    def generate_quarter_windows(self, collection):
        
        output_data = {}
        # Predicting optimal collection windows for each firm
        for cik, dates in list(collection.items()):
            if dates:  # Check if the list of dates is not empty
                quarter_windows = sec_calendar.predict_focus_windows(cik, dates)
                output_data[cik] = quarter_windows
                print(f"CIK: {cik}, Quarter Windows: {quarter_windows}")
                
        output_file_path = "/Users/apple/PROJECT/Code_4_calendar/finance_calendars/src/finance_calendars/sec_calendar_output.json"
        with open(output_file_path, 'w') as f:
            json.dump(output_data, f, indent=4)
            
    def push_metadata(session, xcom_data, type, metadata_class):
        """
        Push the XCom data to the PostgreSQL meta data
        """
        cik_ticker = xcom_data.get('cik_ticker', {})  # Extract cik_ticker from Xcom
        for cik, ticker in cik_ticker.items():
            record = session.query(metadata_class).filter_by(ticker=ticker).first()
            download_date = datetime.now().date()

            if record:
                record.status = 'pending'
                record.download_date = download_date
                record.is_deleted = False
                record.filing_type = type
            else:
                new_record = metadata_class(
                    ticker=ticker,
                    download_date=download_date,
                    status='pending',
                    is_deleted=False,
                    filing_type=type
                )
                session.add(new_record)

        session.commit()
    
    def update_firm_status(self, session, ticker, metadata_class, success=True):
        """
        Update the status of a specific ticker in the metadata.

        Args:
            session: SQLAlchemy session object.
            ticker: The ticker symbol to update.
            success: Boolean indicating whether the download was successful (default: True).

        Returns:
            None
        """
        try:
            # Query the metadata table for the given ticker
            record = session.query(metadata_class).filter_by(ticker=ticker).first()

            if record:
                if success:
                    # Update the record as completed
                    record.status = 'completed'
                    record.is_deleted = False
                    record.recent_update_date = datetime.now()
                    print(f"Updated status for ticker: {ticker} to 'completed'")
                else:
                    # Mark the record as failed
                    record.status = 'failed'
                    record.recent_update_date = datetime.now()
                    print(f"Updated status for ticker: {ticker} to 'failed'")
            else:
                print(f"No record found for ticker: {ticker}")

            # Commit the changes to the database
            session.commit()

        except Exception as e:
            # Log any exceptions that occur
            session.rollback()
            print(f"Error updating status for ticker: {ticker}. Error: {e}")
    
    def check_if_data_downloaded(self, session, xcom_data, metadata_class):
        """
        Check if the data for the ticker is already downloaded from the metadata table.

        Args:
            session: SQLAlchemy session object.
            xcom_data: Dictionary containing schedule data (e.g., CIKs and tickers).
            metadata_class: The metadata class to query (e.g., SECMetadata, CallsMetadata).

        Returns:
            list: List of tickers that have already been downloaded.
        """
        cik_ticker = xcom_data.get('cik_ticker', {})  # Extract CIK-ticker mapping from XCom data
        tickers = list(cik_ticker.values())  # Get the list of tickers

        # Query the database for completed and non-deleted records
        downloaded_tickers = session.query(metadata_class.ticker).filter(
            metadata_class.ticker.in_(tickers),  # Check if the ticker is in the provided list
            metadata_class.status == 'completed',  # Ensure the status is 'completed'
            metadata_class.is_deleted == False  # Ensure the record is not marked as deleted
        ).all()

        # Extract the tickers from the query result and return as a list
        return [ticker[0] for ticker in downloaded_tickers]
        

    def update_list_of_firms(self, session, xcom_data, metadata_class):
        """
        Update the list of firms in the XCom data by removing already downloaded tickers.

        Args:
            session: SQLAlchemy session object.
            xcom_data: Dictionary containing schedule data (e.g., CIKs and tickers).
            metadata_class: The metadata class to query (e.g., SECMetadata, CallsMetadata).

        Returns:
            None: Updates the `xcom_data` in place.
        """
        # Get the list of already downloaded tickers
        downloaded_tickers = self.check_if_data_downloaded(session, xcom_data, metadata_class)

        # Filter out the downloaded tickers from the CIK-ticker mapping
        xcom_data['cik_ticker'] = {
            cik: ticker
            for cik, ticker in xcom_data['cik_ticker'].items()
            if ticker not in downloaded_tickers
        }
        
    def plot_date_distribution_by_quarter(self, dates_list):
        """Plot the distribution of dates grouped by quarter."""
        dates = pd.to_datetime(dates_list)
        df = pd.DataFrame({"date": dates})
        df["quarter"] = df["date"].dt.month.apply(self.get_quarter)
        df["day_of_year"] = df["date"].dt.dayofyear

        # Plot the distribution
        plt.figure(figsize=(10, 6))
        sns.boxplot(x="quarter", y="day_of_year", data=df, palette="Set2")
        plt.title("Distribution of Dates by Quarter")
        plt.xlabel("Quarter")
        plt.ylabel("Day of Year")
        plt.xticks([0, 1, 2, 3], ["Q1", "Q2", "Q3", "Q4"])
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.show()



# Example usage - If you want to run this code, make sure to set the folder paths correctly.
# folder_path_10q = '/Users/apple/PROJECT/Code_4_SECfilings/total_sp500_10q-html'
# folder_path_10k = '/Users/apple/PROJECT/Code_4_SECfilings/total_sp500_10k-html'
# sec_calendar = SecCalender(folder_path_10q, folder_path_10k)
# firm_path_dict_10q = sec_calendar.get_firm_paths_dict(folder_path_10q)
# firm_path_dict_10k = sec_calendar.get_firm_paths_dict(folder_path_10k)
# firms_collection = sec_calendar.get_sec_release_dates(firm_path_dict_10q, firm_path_dict_10k)


folder_path_10q = '' # Placeholder
folder_path_10k = '' # Placeholder
sec_calendar = SECCalender(folder_path_10q, folder_path_10k)
json_file_path = "/opt/airflow/data/calenders/sec_predicted_calendar_output.json"
ciks = sec_calendar.fetch_sec_calendars(json_file_path)
print(f"CIKs with overlapping dates for today: {ciks}")
