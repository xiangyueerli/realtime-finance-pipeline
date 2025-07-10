from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import io
import csv
import pandas as pd
from .constants import MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME, DB_NAME, \
                    ANNUAL_REPORT_COLLECTION, COMPANY_TICKER_DATA

# Connect to MongoDB with authentication
client = MongoClient(f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/")
db = client[DB_NAME]


# Function to upload a file/document with duplicate checks
def upload_file(collection_name, file_data, check_fields):
    collection = db[collection_name]
    # Check if a similar document already exists
    duplicate = collection.find_one({field: file_data[field] for field in check_fields})
    if duplicate:
        print("Duplicate entry found. File not uploaded.")
    else:
        result = collection.insert_one(file_data)
        print(f"File uploaded with ID: {result.inserted_id}")

def get_file_size_in_mb(file_path):
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


# Function to list all files/documents
def list_files(collection_name):
    collection = db[collection_name]
    files = collection.find()
    counter = 0
    for file in files:
        counter += 1
        # print(file)
        # break
    print("Total entries in the collection: ", counter)


# Function to filter files based on criteria
def filter_files(collection_name, filter_criteria):
    collection = db[collection_name]  # Dynamically access the collection
    results = collection.find(filter_criteria)  # Perform the query
    return results


def search_articles(collection_name, filter_criteria):
    """
    Search for articles based on a list of search queries.
    Returns the aggregated results.
    """
    collection = db[collection_name]  # Dynamically access the collection
    # Build the $or query
    or_conditions = [{"headline": {"$regex": query, "$options": "i"}} for query in filter_criteria] + \
                    [{"content": {"$regex": query, "$options": "i"}} for query in filter_criteria]
    
    query = {"$or": or_conditions}
    
    # Fetch matching documents
    results = list(collection.find(query))
    return results

def parse_csv_data(csv_data):
    try:
        csvfile = io.StringIO(csv_data)
        df = pd.read_csv(csvfile)
        return df
    except Exception as e:
        print(f"Error parsing CSV data: {e}")
        return pd.DataFrame()


# # Example usage
# if __name__ == "__main__":
#     # Replace this with the path to your data folder
#     root_folder = "/data/mongodb/mongo_data_dir/data_financial_rag"
#     for root, dirs, files in os.walk(root_folder):
#         for file in files:
#             components = root.split("/data_financial_rag/")[-1].split("/")
#             try:
#                 ticker = file.split("_")[1].split(".pdf")[0]
#                 results = filter_files(COMPANY_TICKER_DATA, {"Ticker": ticker})
#                 report_data = {
#                     "year": int(components[1]),
#                     "file_path": root + "/" + file,
#                     "company": file.split("_")[0],
#                     "ticker_symbol": ticker,
#                     "company_ticker_id": results[0]["_id"],
#                     "metadata": {
#                         "size_mb": get_file_size_in_mb(root + "/" + file),
#                         "uploaded_date": datetime.now().strftime("%Y-%m-%d")
#                     }
#                 }
#                 upload_file(ANNUAL_REPORT_COLLECTION, report_data, ["company", "year", "ticker_symbol"])
#             except Exception as e:
#                 print(e)
#     list_files(ANNUAL_REPORT_COLLECTION)
  
    # results = query_across_collections("Lysogene SA", "2022-01-01", "2023-05-21")
    # print("Company Files:", results["company_files"])
    # print("News Articles:", results["news_articles"])
    # print("Price Data:", results["price_data"])