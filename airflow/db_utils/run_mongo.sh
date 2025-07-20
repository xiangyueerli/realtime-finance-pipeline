################################################################################
# Author: Chunyu Yan
# Date: 2025-07-13
# Title: Basic MongoDB Shell Operations for Financial Data
# Description:
#     This shell script provides commonly used MongoDB commands to inspect and
#     manage SEC filing data stored in a MongoDB instance.
#     It connects using root credentials and performs typical read/write ops.
################################################################################

# run mongodb
mongo --username root --password mongo_edinburgh_123 --authenticationDatabase admin
use financial_db

# 
show dbs
show collections

# 
db.sec_reports.find().sort({_id: -1}).limit(10)
db.sec_reports.drop()
db.sec_reports.count()
db.sec_reports.findOne() 

#
db.transcripts.find().sort({_id: -1}).limit(1)
db.transcripts.count()

# 
db.company_ticker.find().sort({_id: -1}).limit(1)
db.company_ticker.count()

#
db.company_permid.count()
db.company_permid.find().sort({_id: -1}).limit(1)