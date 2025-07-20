"""
Query Function for SEC Filing Reports in MongoDB

Author: Chunyu Yan
Date: 2025-07-13
Project: Real-time Financial Document Pipeline for AI/LLM Integration

TODO
"""

from typing import List, Optional
from datetime import datetime
from typing import List
from bson import ObjectId

from .constants import *
from .mongo_utils import get_db, filter_files


# Connect to MongoDB with authentication
_, db = get_db()


def find_annual_reports(
    company_ticker_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    """
    Find SEC 10-K annual reports for a specific company_ticker_id within a year range.

    Args:
        collection: MongoDB collection (e.g., sec_report_collection)
        company_ticker_id: ObjectId of the company in the company_ticker collection
        start_date: datetime object representing the start of the range
        end_date: datetime object representing the end of the range

    Returns:
        List of matching annual (10-K) reports
    """

    query = {
        "company_ticker_id": company_ticker_id,
        "report_type": "10-K",
        "year": {"$gte": start_date.year, "$lte": end_date.year}
    }
    collection = db[SEC_REPORT_COLLECTION]

    results = list(collection.find(query))
    return results


def find_quarter_reports(
    company_ticker_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    """
    Find SEC 10-Q filings for a specific company_ticker_id within a date range.

    Args:
        collection: MongoDB collection (e.g., sec_report_collection)
        company_ticker_id: ObjectId of the company in the company_ticker collection
        start_date: datetime object representing the start of the range
        end_date: datetime object representing the end of the range

    Returns:
        List of matching quarterly reports (10-Q)
    """

    # Define MongoDB query: select 10-Q reports in year range
    # Filter quarter by full year which is rough
    query = {
        "company_ticker_id": company_ticker_id,
        "report_type": "10-Q",
        "year": {"$gte": start_date.year, "$lte": end_date.year},
        "quarter": {"$regex": "^q[1-4]$", "$options": "i"}
    }
    
    collection = db[SEC_REPORT_COLLECTION]

    raw_results = list(collection.find(query))
    filtered = []

    # Filter quarter finely
    quarter_month_map = {
        "q1": (1, 3),
        "q2": (4, 6),
        "q3": (7, 9),
        "q4": (10, 12)
    }

    for report in raw_results:
        year = report.get("year")
        quarter = report.get("quarter", "").lower()
        if quarter not in quarter_month_map:
            continue

        start_month, end_month = quarter_month_map[quarter]
        quarter_start = datetime(year, start_month, 1)
        quarter_end = datetime(year, end_month, 1).replace(day=28)
        quarter_end = quarter_end.replace(day=28) + (quarter_end.replace(day=4) - quarter_end)

        if quarter_end >= start_date and quarter_start <= end_date:
            filtered.append(report)

    return filtered



def find_transcripts(
    company_ticker_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    """
    Find earnings call transcripts for a company within a time range.

    Args:
        collection: MongoDB collection storing transcripts
        company_ticker_id: ObjectId referencing the company in the ticker table
        start_date: datetime object for start of range
        end_date: datetime object for end of range

    Returns:
        List of matching transcript documents
    """
    
    query = {
        "company_ticker_id": company_ticker_id,
        "call_date": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    collection = db[EARNING_CALL_COLLECTION]

    results = list(collection.find(query))
    return results



# Function to query across all collections
def query_across_collections(company_name, start_date, end_date):
    ## can integrate fuzzy matching in this
    results_ticker = list(filter_files(COMPANY_TICKER_DATA, {"Company Name": company_name}))
    results_permid = list(filter_files(COMPANY_PERMID_DB, {"companyName": company_name}))
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    ticker_id, perm_id = None, None
    if len(results_ticker)>0:
        ticker_id = results_ticker[0]["_id"]
        print("ticker_id: ", ticker_id)
    if len(results_permid)>0:
        perm_id = results_permid[0]["_id"]
        print("perm_id: ", perm_id)
    
    final_response = {}
    
    if ticker_id:
        final_response["annual_reports"] = find_annual_reports(ticker_id, start_date, end_date)
        final_response["quarter_reports"] = find_quarter_reports(ticker_id, start_date, end_date)
        final_response["transcripts"] = find_transcripts(ticker_id, start_date, end_date)
        # final_response["price_data"] = find_price_data(start_date, end_date, ticker_id)

    # if perm_id:
        # final_response["news_data"] = find_news_data(start_date, end_date, perm_id)
        ## you can also use search_articles function to retrieve relevant news by searching within headlines

    return final_response
















def query_sec_reports(
    collection,
    cik: int,
    start_year: int,
    end_year: int,
    report_type: Optional[str] = None,
    fields: Optional[List[str]] = None
) -> List[dict]:

    # Build query
    query = {
        "CIK": cik,
        "year": {"$gte": start_year, "$lte": end_year}
    }
    if report_type:
        query["report_type"] = report_type
        
    print("Query:", query)
    print("Type:", type(query))

    # Build projection, 需要返回的字段
    projection = None
    if fields is not None:
        projection = {field: 1 for field in fields}
        projection["_id"] = 0  # Exclude MongoDB internal ID

    # Query database
    results = list(collection.find(query))

    return results
