"""
SEC Report Data Pipeline and Query Utilities

Author: Chunyu Yan
Date: 2025-07-01
Description:
    This script provides functionality for:
    1. Extracting and uploading SEC filings (10-K and 10-Q) from local txt/html/pdf files
       into a MongoDB collection with metadata and deduplication.
    2. Querying reports by CIK and year range, optionally filtering by report type.
"""

import pandas as pd
from tqdm import tqdm
import json
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from .mongo_utils import get_db, upload_file, filter_files, get_file_size_in_mb
from .constants import COMPANY_TICKER_DATA, SEC_REPORT_COLLECTION


# Connect to MongoDB with authentication
_, db = get_db()


def get_quarter(date):
    """Return fiscal quarter for a given datetime object."""
    month = date.month
    # Calculate the quarter
    quarter = (month - 1) // 3 + 1
    return quarter


def is_10k_file(json_file_path, cik, date_str):
    """Check whether a given (CIK, date) pair corresponds to a 10-K report."""
    if not os.path.exists(json_file_path):
        print(f"JSON file not found: {json_file_path}")
        return False
    with open(json_file_path, 'r', encoding='utf-8') as f:
        dic = json.load(f)
    if cik in dic:
        k10_list = dic[cik]
        if date_str in k10_list:
            return True
    return False
        

def push_sec_reports():
    """
    Extract and upload SEC 10-K and 10-Q filings into MongoDB from local file system.

    This function walks through the local directory structure containing txt, html, and pdf
    versions of SEC filings for various companies, identifies the report type (10-K or 10-Q)
    based on an external JSON mapping file, and uploads the content along with metadata 
    (such as year, quarter, CIK, ticker, and file size) to the MongoDB collection.

    Deduplication is enforced using a combination of keys such as CIK, year, report_type,
    and quarter (for 10-Q only).

    Requirements:
        - Local folder structure must contain /txt, /html, and /pdf directories with 
          subfolders named by CIK and files named by date (e.g., 2023-03-15.txt).
        - k10_list.json should be present in the /pdf folder to distinguish 10-K filings.
        - Ticker and CIK mappings must be available in the QQQ_constituents.csv file.

    Output:
        Uploads structured reports into the SEC_REPORT_COLLECTION in MongoDB.
    
    Dependencies:
    - pandas
    - tqdm
    - pymongo
    - local utils: mongo_utils.py, constants.py
    """
    
    df = pd.read_csv('/data/seanchoi/airflow/data/QQQ_constituents.csv')
    base_data_folder = '/data/seanchoi/airflow/data/SP500/sec/market'
    txt_base = os.path.join(base_data_folder, "txt")
    html_base = os.path.join(base_data_folder, "html")
    pdf_base = os.path.join(base_data_folder, "pdf")
    k10_json_path = os.path.join(pdf_base, "k10_list.json")

    with open(k10_json_path, "r") as f:
        k10_dict = json.load(f)

    for root, dirs, files in os.walk(txt_base):
        if root.split("/")[-1].startswith("0"):
            cik_str = root.split("/")[-1]
            try:
                cik_no = int(cik_str)
            except:
                continue

            valid_row = df[df["CIK"] == cik_no]
            if valid_row.empty:
                logger.warning(f"CIK {cik_no} not found in constituents file.")
                continue

            for file in tqdm(files):
                try:
                    date_str = file.replace(".txt", "")
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    logger.warning(f"Invalid date format in file name: {file}")
                    continue

                txt_path = os.path.join(txt_base, cik_str, file)
                html_path = os.path.join(html_base, cik_str, file.replace(".txt", ".html"))
                pdf_path = os.path.join(pdf_base, cik_str, file.replace(".txt", ".pdf"))

                try:
                    with open(txt_path, "r", encoding="ISO-8859-1") as f:
                        txt_content = f.read()
                except:
                    txt_content = None
                    logger.warning(f"Missing txt content: {txt_path}")

                try:
                    with open(html_path, "r", encoding="ISO-8859-1") as f:
                        html_content = f.read()
                except:
                    html_content = None
                    logger.warning(f"Missing html content: {html_path}")

                is_10k = False
                date_str_for_check = date_str
                if cik_str in k10_dict and date_str_for_check in k10_dict[cik_str]:
                    is_10k = True

                report_type = "10-K" if is_10k else "10-Q"
                quarter = None if is_10k else "q" + str(get_quarter(date_obj))

                logger.info(f"Processing {report_type} for {valid_row.iloc[0]['Symbol']} on {date_str}")

                try:
                    results = filter_files(COMPANY_TICKER_DATA, {"Ticker": valid_row.iloc[0]["Symbol"]})
                    report_data = {
                        "year": int(date_str.split("-")[0]),
                        "quarter": quarter,
                        "publish_date": date_str,
                        "report_type": report_type,
                        "company": valid_row.iloc[0]["Security"],
                        "ticker_symbol": valid_row.iloc[0]["Symbol"],
                        "company_ticker_id": results[0]["_id"],
                        "html_content": html_content,
                        "txt_content": txt_content,
                        "html_path": html_path,
                        "txt_path": txt_path,
                        "pdf_path": pdf_path,
                        "metadata": {
                            "uploaded_date": datetime.now().strftime("%Y-%m-%d"),
                            "size_mb": get_file_size_in_mb(root + "/" + file),
                            "CIK": cik_no
                        }
                    }
                    
                    unique_keys = ["company", "year", "ticker_symbol", "report_type"]
                    if report_type == "10-Q":
                        unique_keys.append("quarter")

                    upload_file(SEC_REPORT_COLLECTION, report_data, unique_keys)

                except Exception as e:
                    logger.error(f"Failed to process {file} for CIK {cik_no}: {str(e)}")