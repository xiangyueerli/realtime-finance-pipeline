"""
Author: Chunyu Yan
Date: 2025-08-02
"""

import os
import json
from datetime import datetime
from dateutil import tz
from tqdm import tqdm

from .mongo_utils import get_db, upload_file
from .constants import PEER_COLLECTION

# Connect to MongoDB
_, db = get_db()


def push_peer_file(json_data: dict, source_path: str, main_ticker: str):
    """
    Wrap peer info of a main stock and upload to MongoDB.

    Args:
        json_data (dict): Raw JSON from API per stock.
        source_path (str): File path of the JSON.
        main_ticker (str): Main stock symbol (e.g., AAPL).

    Returns:
        None
    """
    peers_raw = json_data.get("data", [])
    included = json_data.get("included", [])
    uploaded_dt = datetime.now(tz=tz.UTC)

    # Build peer company list
    peers = []
    for item in peers_raw:
        attr = item.get("attributes", {})
        rel = item.get("relationships", {})
        peers.append({
            "ticker": attr.get("name"),
            "company": attr.get("company"),
            "exchange": attr.get("exchange"),
            "followers_count": attr.get("followersCount", 0),
            "article_count": attr.get("articleRtaCount", 0),
            "news_count": attr.get("newsRtaCount", 0),
            "fund_type_id": attr.get("fundTypeId", None),
            "sector_id": rel.get("sector", {}).get("data", {}).get("id"),
            "sub_industry_id": rel.get("subIndustry", {}).get("data", {}).get("id")
        })

    # Extract sector and sub_industry info from included
    sector_info = {}
    sub_industry_info = {}
    for item in included:
        attr = item.get("attributes", {})
        meta = item.get("meta", {})
        screener = meta.get("screener_links", {}).get("canonical", "")
        if item["type"] == "sector":
            sector_info = {
                "id": item["id"],
                "name": attr.get("name"),
                "quant_tickers_count": attr.get("quant_tickers_count"),
                "url": screener
            }
        elif item["type"] in ["subIndustry", "sub_industry"]:
            sub_industry_info = {
                "id": item["id"],
                "name": attr.get("name"),
                "quant_tickers_count": attr.get("quant_tickers_count"),
                "url": screener
            }

    # Compose document
    result = {
        "main_ticker": main_ticker,
        "peers": peers,
        "sector_info": sector_info,
        "sub_industry_info": sub_industry_info,
        "meta": {
            "uploaded_date": uploaded_dt.isoformat(),
            "source_file": source_path
        }
    }

    # Upsert by main_ticker
    upload_file(PEER_COLLECTION, result, ["main_ticker"])


def merge_peer_data_files(root_path: str):
    """
    Batch upload all peer JSON files in the given directory.

    Args:
        root_path (str): Directory containing <TICKER>.json files.

    Returns:
        None
    """
    count = 0
    for file in tqdm(sorted(os.listdir(root_path))):
        if not file.endswith(".json"):
            continue
        main_ticker = file.replace(".json", "")
        full_path = os.path.join(root_path, file)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            push_peer_file(json_data, source_path=full_path, main_ticker=main_ticker)
            count += 1
        except Exception as e:
            print(f"[ERROR] Failed to process {full_path}: {e}")
    print(f"[DONE] Processed and uploaded {count} peer files.")


if __name__ == "__main__":
    root = "/data/seanchoi/airflow/data/peer_data"
    merge_peer_data_files(root)
