from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import io
import csv
import pandas as pd
from .push_file_data import upload_file, list_files, filter_files
from .constants import MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME, DB_NAME, \
                    QUARTER_REPORT_COLLECTION, COMPANY_TICKER_DATA
from tqdm import tqdm

# Connect to MongoDB with authentication
client = MongoClient(f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/")
db = client[DB_NAME]


# Function to determine the quarter of a given date
def get_quarter(date):
    month = date.month
    # Calculate the quarter
    quarter = (month - 1) // 3 + 1
    return quarter

# 保存季度报告到MongoDB
# 没有考虑一个公司多股票的情况
def merge_ticker_quarter():
    df = pd.read_csv('/data/seanchoi/airflow/data/QQQ_constituents.csv')
    # 10-Q文件处理为txt的文件夹路径
    quarter_data_folder = '/data/seanchoi/airflow/data/SP500/sec/firm/txt'
    # quarter_data_folder = '/data/seanchoi/airflow/data/sector_10-Q_all_txt'

    count= 0
    print(1)
    for root, dirs, files in os.walk(quarter_data_folder):
        if root.split('/')[-1].startswith("0"):
            cik_no = int(root.split('/')[-1])
            valid_row = df[df["CIK"]==cik_no]
            for file in tqdm(files):
                with open(root+"/"+file, "r", encoding="ISO-8859-1") as f:
                    content = f.read()
                
                date = file.split(".")[0].split("-")
                date_obj = datetime.strptime(file.split(".")[0], "%Y-%m-%d")
                try:
                    results = filter_files(COMPANY_TICKER_DATA, {"Ticker": valid_row.iloc[0]["Symbol"]})
                    report_data = {
                        "year": int(date[0]),
                        "quarter": "q"+str(get_quarter(date_obj)),
                        "content": content,
                        "company": valid_row.iloc[0]["Security"],
                        "ticker_symbol": valid_row.iloc[0]["Symbol"],
                        "company_ticker_id": results[0]["_id"],
                        "metadata": {
                            "uploaded_date": datetime.now().strftime("%Y-%m-%d"),
                            "CIK": cik_no
                        }
                    }
                    upload_file(QUARTER_REPORT_COLLECTION, report_data, ["company", "year", "ticker_symbol", "quarter"])
                except Exception as e:
                    print(e)
merge_ticker_quarter()
list_files(QUARTER_REPORT_COLLECTION)



# # Save all quarter reports to a JSON file
# import json
# from bson import ObjectId
# collection = db["quarter_reports"]
    
# # 查询数据（示例：查全部）
# results = list(collection.find({}))  # 或添加过滤条件，如 {"ticker_symbol": "AAPL"}

# # 自定义 JSON 序列化器，专门处理 ObjectId
# class JSONEncoder(json.JSONEncoder):
#     def default(self, o):
#         if isinstance(o, ObjectId):
#             return str(o)  # 将 ObjectId 转为字符串
#         return super().default(o)

# # 保存为 JSON 文件
# with open("quarter_reports.json", "w", encoding="utf-8") as f:
#     json.dump(results, f, cls=JSONEncoder, indent=2, ensure_ascii=False)

# print("✅ 已成功保存为 quarter_reports.json")