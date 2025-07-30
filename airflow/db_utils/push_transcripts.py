"""
Author: Chunyu Yan
Date: 2025-07-28
Module: Earnings Call Transcript Merger

Description:
This script reads cleaned earnings call transcripts from `.parquet` files,
matches each row to a company using CIK, writes the text to `.txt` files,
and uploads structured metadata and content into MongoDB.
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import io
import csv
import pandas as pd
import logging
from tqdm import tqdm

from .mongo_utils import get_db, upload_file, filter_files
from .constants import COMPANY_TICKER_DATA, EARNING_CALL_COLLECTION

# Logger setup
logger = logging.getLogger(__name__)

# Connect to MongoDB with authentication
_, db = get_db()


def get_quarter(date):
    """
    Given a datetime object, return the corresponding fiscal quarter.

    Args:
        date (datetime): A valid datetime object.

    Returns:
        int: Quarter number (1 to 4).
    """
    month = date.month
    quarter = (month - 1) // 3 + 1
    return quarter


def merge_transcripts():
    """
    Main routine to merge cleaned transcript parquet data into MongoDB.

    - Reads company metadata from QQQ constituent CSV.
    - Loads `.parquet` files from `company_df/`.
    - Writes `.txt` versions to a parallel folder.
    - Uploads structured documents into `EARNING_CALL_COLLECTION`.
    """
    # Load mapping CSV between CIK and ticker
    df = pd.read_csv('/data/seanchoi/airflow/data/QQQ_constituents.csv')

    transcripts_data_base = '/data/seanchoi/airflow/data/SP500/calls/market'
    transcripts_parquet_base = os.path.join(transcripts_data_base, 'company_df')
    transcripts_txt_base = os.path.join(transcripts_data_base, 'txt')

    for root, dirs, files in os.walk(transcripts_parquet_base):
        for file in files:
            if file.endswith('.parquet'):
                file_path = os.path.join(root, file)
                try:
                    df_parquet = pd.read_parquet(file_path)
                    logger.info(f"Successfully read: {file_path}, rows: {len(df_parquet)}")
                except Exception as e:
                    logger.warning(f"Failed to read: {file_path}, error: {e}")
                    continue

                for _, row in df_parquet.iterrows():
                    try:
                        name = row['Name']
                        cik_no = int(row['CIK'])
                        date_str = row['Date']
                        content = row['Body']

                        valid_row = df[df["CIK"] == cik_no]
                        if valid_row.empty:
                            logger.warning(f"CIK {cik_no} not matched to any company, skipping.")
                            continue

                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        cik_str = str(cik_no).zfill(10)
                        date_filename = f"{date_str}.txt"
                        cik_dir = os.path.join(transcripts_txt_base, cik_str)
                        txt_file_path = os.path.join(cik_dir, date_filename)

                        # Write .txt file if not already exists
                        if not os.path.exists(txt_file_path):
                            os.makedirs(cik_dir, exist_ok=True)
                            with open(txt_file_path, "w", encoding="utf-8") as f:
                                f.write(content)
                        else:
                            logger.info(f"Skipped existing file: {txt_file_path}")

                        # Prepare document for MongoDB
                        results = filter_files(COMPANY_TICKER_DATA, {"Ticker": valid_row.iloc[0]["Symbol"]})
                        report_data = {
                            "call_date": date_obj,
                            "year": date_obj.year,
                            "quarter": "q" + str(get_quarter(date_obj)),
                            "content": content,
                            "txt_path": txt_file_path,
                            "company": valid_row.iloc[0]["Security"],
                            "ticker_symbol": valid_row.iloc[0]["Symbol"],
                            "company_ticker_id": results[0]["_id"],
                            "metadata": {
                                "uploaded_date": datetime.now().strftime("%Y-%m-%d"),
                                "CIK": cik_no
                            }
                        }

                        upload_file(EARNING_CALL_COLLECTION, report_data,
                                    ["company", "year", "ticker_symbol", "quarter"])
                    except Exception as e:
                        logger.error(f"Error processing row: {e}")
