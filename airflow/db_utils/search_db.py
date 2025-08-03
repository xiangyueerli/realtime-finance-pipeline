
"""
Real-time Financial Document Query Interface

Author: Chunyu Yan
Date: 2025-07-13
Project: Real-time Financial Document Pipeline for AI/LLM Integration

Description:
This module provides interfaces for querying financial documents stored in MongoDB,
including SEC filings (10-K, 10-Q), earnings call transcripts, and Seeking Alpha
stock idea articles. It supports filtering by company, date range, and role.

"""

from typing import List, Literal, Optional
from datetime import datetime
from bson import ObjectId
from collections import Counter

from .constants import *
from .mongo_utils import get_db, filter_files

import io
import pandas as pd

# Connect to MongoDB with authentication
_, db = get_db()


def find_annual_reports(
    company_ticker_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    """
    Query all annual (10-K) SEC filings for a given company and year range.
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
    Query all quarterly (10-Q) SEC filings for a given company and time range,
    with finer filtering based on quarter-to-month mapping.
    """
    query = {
        "company_ticker_id": company_ticker_id,
        "report_type": "10-Q",
        "year": {"$gte": start_date.year, "$lte": end_date.year},
        "quarter": {"$regex": "^q[1-4]$", "$options": "i"}
    }
    collection = db[SEC_REPORT_COLLECTION]
    raw_results = list(collection.find(query))
    filtered = []

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


def find_stock_idea_articles(
    company_name: str,
    start_year: int,
    end_year: int,
    ticker_role: Literal["primary", "secondary", "both"] = "both",
    fuzzy: bool = False,
    limit: Optional[int] = 100
) -> List[dict]:
    """
    Query Seeking Alpha 'Stock Ideas' articles related to a company
    within a given year range and ticker role (primary, secondary, or both).
    """
    _, db = get_db()
    collection = db[STOCK_IDEA_COLLECTION]

    query = {
        "year": {"$gte": str(start_year), "$lte": str(end_year)}
    }

    match_expr = {"company": {"$regex": company_name, "$options": "i"}} if fuzzy else {"company": company_name}

    if ticker_role == "primary":
        query["primary_tickers"] = {"$elemMatch": match_expr}
    elif ticker_role == "secondary":
        query["secondary_tickers"] = {"$elemMatch": match_expr}
    else:
        query["$or"] = [
            {"primary_tickers": {"$elemMatch": match_expr}},
            {"secondary_tickers": {"$elemMatch": match_expr}}
        ]

    cursor = collection.find(query).sort("publish_date", -1)
    if limit:
        cursor = cursor.limit(limit)

    return list(cursor)


def find_transcripts(
    company_ticker_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    """
    Query earnings call transcripts for a company within a date range.
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


def find_news_data(
    company_perm_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    """
    Query news articles from NEWS_COLLECTION by company_perm_id and date range.
    The date filter is based on 'emeaTimestamp'.
    """
    query = {
        "company_perm_id": company_perm_id,
        "emeaTimestamp": {
            "$gte": start_date.isoformat() + "Z",   # "2015-01-01T00:00:00Z"
            "$lte": end_date.isoformat() + "Z"
        }
    }
    collection = db[NEWS_COLLECTION]
    results = list(collection.find(query).sort("emeaTimestamp", 1))  # 可选按时间升序排序
    return results

def parse_csv_data(csv_data):
    try:
        csvfile = io.StringIO(csv_data)
        df = pd.read_csv(csvfile)
        return df
    except Exception as e:
        print(f"Error parsing CSV data: {e}")
        return pd.DataFrame()

def find_price_data(
    company_ticker_id: ObjectId,
    start_date: datetime,
    end_date: datetime
) -> List[dict]:
    price_data_filtered = []
    price_data = list(db[PRICE_COLLECTION].find({
        "company_ticker_id": company_ticker_id
    }))
    for doc in price_data:
        df = parse_csv_data(doc["csv_data"])
        if not df.empty:
            df["as_of_date"] = pd.to_datetime(df["as_of_date"], format="%Y-%m-%d", errors="coerce")
            filtered_df = df[(df["as_of_date"] >= start_date) & (df["as_of_date"] <= end_date)]
            price_data_filtered.append(filtered_df)

    return price_data_filtered

def find_peer_data(ticker_tympol: str) -> list:
    """
    Find peer companies based on company_perm_id.

    Args:
        company_perm_id (ObjectId): ObjectId of the company in company_permid collection.

    Returns:
        List[dict]: List of peer companies (ticker info).
    """
    peer_doc = db[PEER_COLLECTION].find_one({"main_ticker": ticker_tympol})
    if not peer_doc:
        return []

    return peer_doc.get("peers", [])


def query_across_collections(company_name, start_date, end_date):
    """
    Query across multiple collections (10-K, 10-Q, Transcripts, Stock Ideas)
    using company name and date range. Support both ticker and permid matching.
    """
    results_ticker = list(filter_files(COMPANY_TICKER_DATA, {"Company Name": company_name}))
    results_permid = list(filter_files(COMPANY_PERMID_DB, {"companyName": company_name}))
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    ticker_id, perm_id, ticker_tympol = None, None, None

    if len(results_ticker) > 0:
        ticker_id = results_ticker[0]["_id"]
        ticker_tympol = results_ticker[0].get("Ticker", "")
        print("ticker_id: ", ticker_id)
        print("ticker_tympol: ", ticker_tympol)
    if len(results_permid) > 0:
        perm_id = results_permid[0]["_id"]
        print("perm_id: ", perm_id)

    final_response = {}
    if ticker_id:
        final_response["annual_reports"] = find_annual_reports(ticker_id, start_date, end_date)
        final_response["quarter_reports"] = find_quarter_reports(ticker_id, start_date, end_date)
        final_response["transcripts"] = find_transcripts(ticker_id, start_date, end_date)
        final_response["price_data"] = find_price_data(ticker_id, start_date, end_date)
    
    if perm_id:
        final_response["news"] = find_news_data(perm_id, start_date, end_date)
        
    if ticker_tympol:
        final_response["peer_data"] = find_peer_data(ticker_tympol)

    final_response["stock_ideas"] = find_stock_idea_articles(company_name=company_name, start_year=start_date.year, end_year=end_date.year)

    return final_response


def analyze_final_response(final_response):
    """
    Print summary statistics for the query result,
    including counts and year/quarter/author distributions across categories.
    """
    print("========== Annual Reports (10-K) ==========")
    annual_reports = final_response.get("annual_reports", [])
    print(f"Total: {len(annual_reports)}")
    annual_years = [r.get("year") for r in annual_reports if "year" in r]
    year_counter = Counter(annual_years)
    print("Year distribution (10-K):")
    for year, count in sorted(year_counter.items()):
        print(f"  {year}: {count} reports")

    print("\n========== Quarterly Reports (10-Q) ==========")
    quarter_reports = final_response.get("quarter_reports", [])
    print(f"Total: {len(quarter_reports)}")
    quarter_years = [r.get("year") for r in quarter_reports if "year" in r]
    quarter_counter = Counter(quarter_years)
    print("Year distribution (10-Q):")
    for year, count in sorted(quarter_counter.items()):
        print(f"  {year}: {count} reports")
    quarters = [r.get("quarter", "missing") for r in quarter_reports]
    quarter_freq = Counter(quarters)
    print("Quarter distribution (10-Q):")
    for q, count in quarter_freq.items():
        print(f"  {q.upper()}: {count} reports")

    print("\n========== Earnings Call Transcripts ==========")
    transcripts = final_response.get("transcripts", [])
    print(f"Total: {len(transcripts)}")
    transcript_years = [r.get("year") for r in transcripts if "year" in r]
    transcript_year_counter = Counter(transcript_years)
    print("Year distribution (Transcripts):")
    for year, count in sorted(transcript_year_counter.items()):
        print(f"  {year}: {count} transcripts")
    transcript_quarters = [r.get("quarter", "missing") for r in transcripts]
    transcript_quarter_counter = Counter(transcript_quarters)
    print("Quarter distribution (Transcripts):")
    for q, count in transcript_quarter_counter.items():
        print(f"  {q.upper()}: {count} transcripts")
        
    print("\n========== News Articles ==========")
    news = final_response.get("news", [])
    print(f"Total: {len(news)}")
    news_dates = [r.get("emeaTimestamp", "")[:4] for r in news if r.get("emeaTimestamp")]
    news_year_counter = Counter(news_dates)
    print("Year distribution (News):")
    for year, count in sorted(news_year_counter.items()):
        print(f"  {year}: {count} articles")
        
    print("\n========== Price Data ==========")
    price_data = final_response.get("price_data", [])
    print(f"Total: {len(price_data)} documents")

    price_years = []
    for df in price_data:
        if "as_of_date" in df.columns:
            df["as_of_date"] = pd.to_datetime(df["as_of_date"], errors="coerce")
            years = df["as_of_date"].dropna().dt.year.tolist()
            price_years.extend(years)

    price_year_counter = Counter(price_years)
    print("Year distribution (Price Data):")
    for year, count in sorted(price_year_counter.items()):
        print(f"  {year}: {count} daily records")

    print("\n========== Stock Ideas Articles ==========")
    articles = final_response.get("stock_ideas", [])
    print(f"Total: {len(articles)}")
    article_years = [r.get("year") for r in articles if "year" in r]
    article_year_counter = Counter(article_years)
    print("Year distribution (Stock Ideas):")
    for year, count in sorted(article_year_counter.items()):
        print(f"  {year}: {count} articles")
    authors = [r.get("author", "missing") for r in articles]
    author_counter = Counter(authors)
    print("Top 5 authors (by article count):")
    for author, count in author_counter.most_common(5):
        print(f"  {author}: {count} articles")

    print("\n========== Peer Companies ==========")
    peer_data = final_response.get("peer_data", [])
    print(f"Total: {len(peer_data)}")

    tickers = [peer.get("ticker") for peer in peer_data if peer.get("ticker")]
    sectors = [peer.get("sector_id") for peer in peer_data if peer.get("sector_id")]
    sub_industries = [peer.get("sub_industry_id") for peer in peer_data if peer.get("sub_industry_id")]

    ticker_counter = Counter(tickers)
    sector_counter = Counter(sectors)
    sub_industry_counter = Counter(sub_industries)

    print("Peer Ticker Distribution:")
    for ticker, count in ticker_counter.items():
        print(f"  {ticker}: {count}")

    print("Peer Sector ID Distribution:")
    for sid, count in sector_counter.items():
        print(f"  {sid}: {count}")

    print("Peer SubIndustry ID Distribution:")
    for sid, count in sub_industry_counter.items():
        print(f"  {sid}: {count}")
