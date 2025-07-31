"""
News Data Storage Pipeline Utilities

Author: Chunyu Yan
Date: 2025-07-20
"""
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import pandas as pd
from tqdm import tqdm
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from .mongo_utils import get_db, upload_file, filter_files
from .constants import *


# Connect to MongoDB with authentication
_, db = get_db()

def load_merge_news():
    df = pd.read_pickle("/data/seanchoi/airflow/data/news_data/data.pkl")
    news_data = df[1]
    news_data = news_data.drop('id', axis=1)
    return news_data

def merge_news():
    df = load_merge_news()
    for row in tqdm(df.to_dict(orient='records'), desc="News Upload", unit="rows"):
        company_name = row["assetName"]
        results = filter_files(COMPANY_PERMID_DB, {"companyName": company_name})
        try:
            row["company_perm_id"] = results[0]["_id"]
            row["metadata"] = {
                "uploaded_date": datetime.now().strftime("%Y-%m-%d")
            }
            upload_file(NEWS_COLLECTION, row, ["emeaTimestamp", "headline", "assetName"])
        except Exception as e:
            print(row, "Row not pushed")
