"""
MongoDB Utilities for SEC Report Pipeline

Author: Chunyu Yan
Date: 2025-07-08    
Description:
    This module provides utility functions to:
    - Connect to MongoDB using authentication
    - Upload structured data with duplicate checking
    - Convert BSON ObjectId to strings for JSON compatibility
    - Export MongoDB query results to local JSON files
    - Compute file sizes for metadata logging
    - Filter documents from MongoDB collections

    These tools support the SEC filing data pipeline for storing, managing, 
    and retrieving heterogeneous financial documents for downstream use.

Dependencies:
    - pymongo
    - bson
    - local constants: MONGO_HOST, MONGO_PORT, DB_NAME, etc.
"""

import json, os
from bson import ObjectId
from pymongo import MongoClient
import logging
logger = logging.getLogger(__name__)

from .constants import MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME, DB_NAME

client = None
_db = None

def get_db():
    """
    Establish and return a MongoDB client and database object.
    Uses credentials from constants module.
    Returns:
        (MongoClient, Database): Tuple of client and DB handle
    """
    global _db, client
    # if not _db:   # ❎ 数据库没有实现bool
    if _db is None:
        client = MongoClient(f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/")
        _db = client[DB_NAME]
    return client, _db


# ObjectId 处理方式 1：手动转字符串
def convert_objectid(doc):
    """
    Recursively convert all ObjectId values in a document to string.
    Parameters:
        doc (dict): MongoDB document possibly containing ObjectId values
    Returns:
        dict: Document with all ObjectIds converted to strings
    """
    for k, v in doc.items():
        if type(v) == ObjectId:
            doc[k] = str(v)
        elif type(v) == dict:
            doc[k] = convert_objectid(v)
    return doc


# save mongo data to json file
def save_json(cursor, save_file):
    """
    Save MongoDB cursor results to a JSON file, converting ObjectId to strings.
    Parameters:
        cursor: MongoDB query cursor
        save_file (str): Output file path
    """
    data = [convert_objectid(doc) for doc in cursor]
    with open(save_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)

    print("导出成功，共导出", len(data), "条记录。")


# Function to upload a file/document with duplicate checks
def upload_file(collection_name, file_data, check_fields):
    """
    Upload a document to MongoDB, checking for duplicates based on specified fields.
    Parameters:
        collection_name (str): Name of the MongoDB collection
        file_data (dict): Document to insert
        check_fields (list[str]): Fields used to detect duplicates
    """
    _, db = get_db()
    collection = db[collection_name]
    # Check if a similar document already exists
    duplicate = collection.find_one({field: file_data[field] for field in check_fields})
    if duplicate:
        print("Duplicate entry found. File not uploaded.")
    else:
        result = collection.insert_one(file_data)
        print(f"File uploaded with ID: {result.inserted_id}")


def get_file_size_in_mb(file_path):
    """
    Return the size of a file in megabytes.
    Parameters:
        file_path (str): Path to the file
    Returns:
        float: File size in MB (rounded to 2 decimals), or None if file not found
    """
    try:
        # Get the file size in bytes
        file_size_bytes = os.path.getsize(file_path)
        # Convert bytes to megabytes (MB)
        file_size_mb = file_size_bytes / (1024 * 1024)
        return round(file_size_mb, 2)  # Round to 2 decimal places
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

# Function to filter files based on criteria
def filter_files(collection_name, filter_criteria):
    """
    Query documents from a MongoDB collection based on filter criteria.
    Parameters:
        collection_name (str): Name of the MongoDB collection
        filter_criteria (dict): MongoDB query dictionary
    Returns:
        Cursor: MongoDB query result
    """
    _, db = get_db()
    collection = db[collection_name]  # Dynamically access the collection
    results = collection.find(filter_criteria)  # Perform the query
    return results
