import csv
from pymongo import MongoClient
from .constants import *
from .mongo_utils import get_db

COLLECTION_LIST = [
    "annual_reports",
    "quarter_reports",
    "sec_reports",
    "news_articles",
    "price_data",
    "transcripts",
    "stock_ideas",
    "peer_data",
    "company_permid",
    "company_ticker"
]

OUTPUT_CSV_FILE = "collection_stats.csv"

def export_collection_stats_to_csv():
    # 连接 MongoDB
    _, db = get_db()

    rows = []
    for coll_name in COLLECTION_LIST:
        try:
            stats = db.command("collstats", coll_name)
            row = {
                "collection_name": coll_name,
                "document_count": stats["count"],
                "data_size_MB": round(stats["size"] / 1024 / 1024, 2),
                "storage_size_MB": round(stats["storageSize"] / 1024 / 1024, 2),
                "free_storage_size_MB": round(stats.get("freeStorageSize", 0) / 1024 / 1024, 2),
                "avg_document_size_bytes": stats.get("avgObjSize", 0),
            }
            rows.append(row)
        except Exception as e:
            print(f"Error with collection '{coll_name}': {e}")

    # 写入 CSV 文件
    with open(OUTPUT_CSV_FILE, mode="w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Collection statistics exported to {OUTPUT_CSV_FILE}")