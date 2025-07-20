from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os
import io
import csv
import pandas as pd
import logging
logger = logging.getLogger(__name__)

from .mongo_utils import get_db, upload_file, filter_files
from .constants import COMPANY_TICKER_DATA, EARNING_CALL_COLLECTION
from tqdm import tqdm

# Connect to MongoDB with authentication
_, db = get_db()


def get_quarter(date):
    """Return fiscal quarter for a given datetime object."""
    month = date.month
    # Calculate the quarter
    quarter = (month - 1) // 3 + 1
    return quarter

def merge_transcripts():
    df = pd.read_csv('/data/seanchoi/airflow/data/QQQ_constituents.csv')

    transcripts_data_base = '/data/seanchoi/airflow/data/SP500/calls/market'
    transcripts_parquet_base = os.path.join(transcripts_data_base, 'company_df')
    transcripts_txt_base = os.path.join(transcripts_data_base, 'txt')

    for root, dirs, files in os.walk(transcripts_parquet_base):
        for file in files:
            if file.endswith('.parquet'):
                file_path = os.path.join(root, file)
                try:
                    df_parquet = pd.read_parquet(file_path)
                    logger.info(f"成功读取: {file_path}, 行数: {len(df_parquet)}")
                except Exception as e:
                    logger.warning(f"读取失败: {file_path}, 错误: {e}")
                    continue

                for _, row in df_parquet.iterrows():
                    try:
                        name = row['Name']
                        cik_no = int(row['CIK'])
                        date_str = row['Date']
                        content = row['Body']

                        valid_row = df[df["CIK"] == cik_no]
                        if valid_row.empty:
                            logger.warning(f"CIK {cik_no} 未找到匹配公司，跳过")
                            continue

                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        cik_str = str(cik_no).zfill(10)
                        date_filename = f"{date_str}.txt"
                        cik_dir = os.path.join(transcripts_txt_base, cik_str)
                        txt_file_path = os.path.join(cik_dir, date_filename)

                        if not os.path.exists(txt_file_path):
                            os.makedirs(cik_dir, exist_ok=True)
                            with open(txt_file_path, "w", encoding="utf-8") as f:
                                f.write(content)
                        else:
                            logger.info(f"跳过已存在文件: {txt_file_path}")

                        # 构建 MongoDB 插入数据
                        results = filter_files(COMPANY_TICKER_DATA, {"Ticker": valid_row.iloc[0]["Symbol"]})
                        report_data = {
                            "call_date": date_obj,
                            "year": date_obj.year,
                            "quarter": "q" + str(get_quarter(date_obj)),
                            "content": content,
                            "txt_path": txt_file_path,
                            "company": valid_row.iloc[0]["Security"],
                            "ticker_symbol": valid_row.iloc[0]["Symbol"],
                            "company_ticker_id": results[0]["_id"],
                            "metadata": {
                                "uploaded_date": datetime.now().strftime("%Y-%m-%d"),
                                "CIK": cik_no
                            }
                        }

                        upload_file(EARNING_CALL_COLLECTION, report_data,
                                    ["company", "year", "ticker_symbol", "quarter"])
                    except Exception as e:
                        logger.error(f"处理行出错: {e}")


