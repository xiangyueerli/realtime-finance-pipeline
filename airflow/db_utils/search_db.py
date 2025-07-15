"""
Query Function for SEC Filing Reports in MongoDB

Author: Chunyu Yan
Date: 2025-07-13
Project: Real-time Financial Document Pipeline for AI/LLM Integration

Description:
    This module provides a function to query structured SEC filings 
    (10-K and 10-Q reports) stored in MongoDB.

    Users can filter by CIK (SEC company ID), year range, and report type.
    Optional support for customized field projection and preview/full text toggling 
    is included.

    This is part of a broader system for managing heterogeneous financial data
    to support document retrieval, analysis, and downstream machine learning models.
"""

from typing import List, Optional
from .mongo_utils import get_db

# Connect to MongoDB with authentication
_, db = get_db()

def query_sec_reports(
    collection,
    cik: int,
    start_year: int,
    end_year: int,
    report_type: Optional[str] = None,
    full_text: bool = False,
    fields: Optional[List[str]] = None
) -> List[dict]:
    """
    Query SEC filings for a given CIK and year range, optionally filtering by report type.

    Parameters:
        collection: MongoDB collection object (e.g., SEC_REPORT_COLLECTION)
        cik (int): CIK number of the company
        start_year (int): Start of year range (inclusive)
        end_year (int): End of year range (inclusive)
        report_type (str or None): "10-K", "10-Q", or None for all types
        full_text (bool): If True, returns full txt_content; else returns preview (default: False)
        fields (list or None): Optional list of fields to return; if None, returns all

    Returns:
        List of matching report documents (with truncated or full text)
    """

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
