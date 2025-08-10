from datetime import datetime
import pandas as pd
from tqdm import tqdm
from .constants import *
from .mongo_utils import *

_, db = get_db()

TRNA_CMPNY_path = "/data/seanchoi/airflow/data/company_list/TRNA.CMPNY.EN.BASIC.110.txt"
TRNA_Ticker_path = "/data/seanchoi/airflow/data/company_list/TRNA.Mapping.EN.PermId.Ticker.110.txt"
stock_ticker_path = "/data/seanchoi/airflow/data/company_list/stock_ticker.csv"

# SETUP FOR THE PERMID DATA
def extract_permid_company_data():
    df_comp_name = pd.read_csv(TRNA_CMPNY_path, sep="\t")
    df_comp_name = df_comp_name.drop_duplicates("PermID")
    df_ticker = pd.read_csv(TRNA_Ticker_path, sep="\t")
    df_ticker = df_ticker.drop_duplicates("PermID")
    df_ticker = df_ticker[["PermID", "Ticker", "MIC"]]
    df_permid_data = pd.merge(df_comp_name, df_ticker, on="PermID")
    return df_permid_data

def extract_ticker_data():
    df_ticker_stock = pd.read_csv(stock_ticker_path)
    return df_ticker_stock

def merge_company_data():
    df_permid_table = extract_permid_company_data()
    df_ticker_table = extract_ticker_data()
    print(len(df_permid_table))
    # Upload permid data with progress bar
    print("Uploading PermID data...")
    for row in tqdm(df_permid_table.to_dict(orient='records'), desc="PermID Upload", unit="rows"):
        row["metadata"] = {
            "uploaded_date": datetime.now().strftime("%Y-%m-%d")
        }
        # Ticker is the unique id which should not have clashes and thus that is used for checking duplicates
        upload_file(COMPANY_PERMID_DB, row, ["PermID"])

    # Upload ticker data with progress bar
    print("Uploading Ticker data...")
    for row in tqdm(df_ticker_table.to_dict(orient='records'), desc="Ticker Upload", unit="rows"):
        row["metadata"] = {
            "uploaded_date": datetime.now().strftime("%Y-%m-%d")
        }
        # Ticker is the unique id which should not have clashes and thus that is used for checking duplicates
        upload_file(COMPANY_TICKER_DATA, row, ["Ticker"])

    # List uploaded files
    print("Listing uploaded Ticker data files...")
    list_files(COMPANY_TICKER_DATA)
