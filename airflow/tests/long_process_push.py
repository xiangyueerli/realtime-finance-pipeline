"""
Author: Chunyu Yan
Date: 2025-08-02

# This scripts can be used to run long process like merge_news in tmux.
"""

import sys
import os
import time
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from collections import Counter
from datetime import datetime
from bson import ObjectId
from datetime import datetime
from db_utils import *

start_time = time.time()

# merge_news()
# merge_news_batch()

root = "/data/seanchoi/airflow/data/stock_ideas"
merge_stock_idea_articles(root)

end_time = time.time()
elapsed_time = end_time - start_time

print(f"Function has took {elapsed_time:.2f} seconds")