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


# improvement for pushing news data
BATCH_SIZE = 100
CHUNK_SIZE = 1000  # For querying existing dedup_keys in safe chunks


def get_perm_id_cache():
    """
    Returns a cached lookup function to get company_perm_id by company name.
    This avoids redundant MongoDB queries and handles missing cases gracefully.
    """
    perm_id_cache = {}
    missing_names = set()  # Track assetNames not found

    def get_perm_id(company_name):
        if company_name in perm_id_cache:
            return perm_id_cache[company_name]
        results = list(filter_files(COMPANY_PERMID_DB, {"companyName": company_name}))
        if results:
            perm_id = results[0]["_id"]
            perm_id_cache[company_name] = perm_id
            return perm_id
        else:
            missing_names.add(company_name)
            perm_id_cache[company_name] = None
            return None

    get_perm_id.missing_names = missing_names  # Attach set to function for later inspection
    return get_perm_id


def merge_news_batch():
    # 1. Load preprocessed news DataFrame
    df = load_merge_news()
    df.drop(columns=["id"], inplace=True, errors="ignore")  # drop legacy id field if exists

    # 2. Construct a deduplication key by combining three fields
    df["dedup_key"] = (
        df["emeaTimestamp"].astype(str) + "|" +
        df["headline"].astype(str) + "|" +
        df["assetName"].astype(str)
    )

    # 3. Connect to MongoDB and access the target collection
    _, db = get_db()
    collection = db[NEWS_COLLECTION]

    # 4. Create index on dedup_key to accelerate deduplication lookup
    collection.create_index(
        [("dedup_key", 1)],
        name="dedup_key_index"
    )

    # 5. Query existing dedup_keys from MongoDB to filter out duplicates
    dedup_keys = df["dedup_key"].unique().tolist()
    existing_keys = set()
    for i in range(0, len(dedup_keys), CHUNK_SIZE):
        chunk = dedup_keys[i:i + CHUNK_SIZE]
        cursor = collection.find({"dedup_key": {"$in": chunk}}, {"dedup_key": 1})
        for doc in cursor:
            existing_keys.add(doc["dedup_key"])

    # 6. Filter out rows that already exist in the database
    df = df[~df["dedup_key"].isin(existing_keys)]

    # 7. Map company name to company_perm_id using cached lookups
    get_perm_id = get_perm_id_cache()
    df["company_perm_id"] = df["assetName"].map(get_perm_id)
    df = df[df["company_perm_id"].notna()]  # remove rows without valid perm_id

    # 8. Add metadata field with upload timestamp (one dict per row)
    upload_date = datetime.now().strftime("%Y-%m-%d")
    df["metadata"] = [{"uploaded_date": upload_date}] * len(df)

    # 9. Convert to list of documents and insert in batches
    records = df.to_dict("records")
    for i in tqdm(range(0, len(records), BATCH_SIZE), desc="Batch Upload", unit="batch"):
        batch = records[i:i + BATCH_SIZE]
        try:
            collection.insert_many(batch, ordered=False)
        except Exception as e:
            print(f"Batch {i} failed:", e)

    # 10. (Optional) Clean up dedup_key field if you don't want to retain it
    # collection.update_many({}, {"$unset": {"dedup_key": ""}})

    # 11. (Optional) Print assetNames that had no perm_id
    if get_perm_id.missing_names:
        print(f"{len(get_perm_id.missing_names)} company names not found in perm_id mapping:")
        for name in sorted(get_perm_id.missing_names):
            print(f"  - {name}")
