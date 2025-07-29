import os
import json
from datetime import datetime
from dateutil import tz
from bs4 import BeautifulSoup
from tqdm import tqdm

from .mongo_utils import get_db, upload_file
from .constants import STOCK_IDEA_COLLECTION

# Connect to MongoDB
_, db = get_db()

def push_stock_idea_article(json_data: dict, source_path: str) -> dict:
    data = json_data["data"]
    included = json_data.get("included", [])
    attributes = data["attributes"]
    relationships = data.get("relationships", {})

    # --- Author ---
    author_id = relationships.get("author", {}).get("data", {}).get("id")
    author_name = None
    for item in included:
        if item["type"] == "author" and item["id"] == author_id:
            author_name = item["attributes"].get("nick") or item["attributes"].get("slug")
            break

    # --- Themes ---
    themes = []
    themes_obj = attributes.get("themes", {})
    for theme_obj in themes_obj.values():
        theme_id = theme_obj.get("id")
        # print(theme_id)
        if not theme_id:
            continue
        for item in included:
            if item["type"] == "tag" and int(item["id"]) == theme_id:
                # print(theme_id, item["attributes"].get("name"))
                themes.append(item["attributes"].get("name"))
                
    print(themes)

    # --- Tickers ---
    def get_tickers(key: str):
        tickers = []
        for tag in relationships.get(key, {}).get("data", []):
            tag_id = tag["id"]
            for item in included:
                if item["type"] == "tag" and int(item["id"]) == tag_id:
                    if item["attributes"].get("tagKind") == "Tags::Ticker":
                        tickers.append(item["attributes"].get("name"))
        return list(set(tickers))

    primary_tickers = get_tickers("primaryTickers")
    secondary_tickers = get_tickers("secondaryTickers")

    # --- HTML / Plain Text ---
    html_content = attributes.get("content", "") or ""
    txt_content = BeautifulSoup(html_content, "html.parser").get_text().strip()

    # --- Time ---
    publish_date_raw = attributes.get("publishOn")
    publish_dt = datetime.fromisoformat(publish_date_raw.replace("Z", "+00:00"))
    publish_dt_utc = publish_dt.astimezone(tz.UTC)
    year = publish_dt_utc.year

    # --- Upload time ---
    uploaded_dt = datetime.now(tz=tz.UTC)

    result = {
        "title": attributes.get("title", ""),
        "html_content": html_content,
        "txt_content": txt_content,
        "author": author_name,
        "year": year,
        "publish_date": publish_dt_utc.isoformat(),
        "themes": themes,
        "commentCount": attributes.get("commentCount", 0),
        "likesCount": attributes.get("likesCount", 0),
        "isExclusive": attributes.get("isExclusive", False),
        "beforeOpeningHours": attributes.get("beforeOpeningHours", False),
        "primary_tickers": primary_tickers,
        "secondary_tickers": secondary_tickers,
        "metadata": {
            "uploaded_date": uploaded_dt.isoformat(),
            "source_file": source_path
        }
    }
    upload_file(STOCK_IDEA_COLLECTION, result, ["title", "publish_date", "author"])

def merge_stock_idea_articles(root_path: str):
    count = 0
    for year_folder in sorted(os.listdir(root_path)):
        year_path = os.path.join(root_path, year_folder)
        if not os.path.isdir(year_path):
            continue
        for file in os.listdir(year_path):
            if not file.endswith(".json"):
                continue
            full_path = os.path.join(year_path, file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                doc = push_stock_idea_article(json_data, source_path=full_path)
                
                count += 1
            except Exception as e:
                print(f"[ERROR] Failed to process {full_path}: {e}")
        break
    print(f"[DONE] Processed and uploaded {count} articles.")

if __name__ == "__main__":
    root = "/data/seanchoi/airflow/data/stock_ideas"
    merge_stock_idea_articles(root)
