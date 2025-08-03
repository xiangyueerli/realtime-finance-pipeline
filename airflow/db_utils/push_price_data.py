"""
Module: price_data_uploader

Author: Chunyu Yan
Date: 2025-08-02

Description:
    This module handles the processing and uploading of daily price data 
    (from JSON to CSV format) into MongoDB.

Workflow:
    1. Read JSON-formatted price data from the specified directory
    2. Convert each file into CSV format (in-memory)
    3. Upload price data with metadata to MongoDB under PRICE_COLLECTION
"""

from datetime import datetime
import os
import io
import csv
import json
import pandas as pd
from tqdm import tqdm

from .mongo_utils import upload_file, filter_files, get_file_size_in_mb, get_db
from .constants import COMPANY_TICKER_DATA, PRICE_COLLECTION

# Initialize MongoDB connection
_, db = get_db()


def upload_price_data(file_path: str, csv_data: str, ticker_symbol: str):
    """
    Upload single price file to MongoDB, mapped to its ticker symbol.

    Args:
        file_path (str): Local path of the source file
        csv_data (str): CSV-format price data string
        ticker_symbol (str): Associated ticker (used to fetch foreign key ID)
    """
    try:
        results = filter_files(COMPANY_TICKER_DATA, {"Ticker": ticker_symbol})
        if not results:
            print(f"[WARNING] Ticker '{ticker_symbol}' not found in COMPANY_TICKER_DATA.")
            return

        price_data = {
            "ticker_symbol": ticker_symbol,
            "file_path": file_path,
            "csv_data": csv_data,
            "company_ticker_id": results[0]["_id"],
            "price_data_frequency": "1d",  # Daily price data
            "metadata": {
                "size_mb": get_file_size_in_mb(file_path),
                "uploaded_date": datetime.now().strftime("%Y-%m-%d")
            }
        }

        upload_file(PRICE_COLLECTION, price_data, ["ticker_symbol", "price_data_frequency"])

    except Exception as e:
        print(f"[ERROR] Failed to upload price data for {ticker_symbol}: {e}")


def merge_ticker_price():
    """
    Iterate through all JSON files in the price data directory,
    convert them into CSV format, and upload each to MongoDB.
    """
    directory = '/data/seanchoi/airflow/data/price_data/'

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and f.endswith(".json")]

    for file in files:
        file_path = os.path.join(directory, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            data_points = json_data.get("data", [])

            # Prepare in-memory CSV stream
            csv_output = io.StringIO()
            columns = ["open", "close", "high", "low", "volume", "div_adj_factor", "as_of_date"]
            writer = csv.writer(csv_output)
            writer.writerow(columns)

            for item in data_points:
                attributes = item.get("attributes", {})
                as_of_date = attributes.get("as_of_date")
                if not as_of_date:
                    continue
                writer.writerow([
                    attributes.get("open"),
                    attributes.get("close"),
                    attributes.get("high"),
                    attributes.get("low"),
                    attributes.get("volume"),
                    attributes.get("div_adj_factor"),
                    datetime.strptime(as_of_date, "%Y-%m-%d").strftime("%Y-%m-%d"),
                ])

            csv_data = csv_output.getvalue()
            csv_output.close()

            ticker_symbol = file.replace(".json", "")
            upload_price_data(file_path, csv_data, ticker_symbol)

        except Exception as e:
            print(f"[ERROR] Failed to process file {file_path}: {e}")
