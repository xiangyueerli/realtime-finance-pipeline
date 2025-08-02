"""
Author: Chunyu Yan
Date: 2025-08.02

# This scripts can be used to run long process like merge_news in tmux.
"""

import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from collections import Counter
from datetime import datetime
from bson import ObjectId
from datetime import datetime
from db_utils import *

merge_news()