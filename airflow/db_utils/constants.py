# MongoDB connection details
MONGO_USERNAME = "root"  # Replace with your MongoDB username
MONGO_PASSWORD = "mongo_edinburgh_123"  # Replace with your MongoDB password

# MONGO_HOST = "mongo_container" # run in the docker
MONGO_HOST = "localhost"  # Uncomment this line if running locally

MONGO_PORT = 27017  # Default MongoDB port
DB_NAME = "financial_db"  # Database name

COMPANY_PERMID_DB = "company_permid"
COMPANY_TICKER_DATA = "company_ticker"

# # for production mode
ANNUAL_REPORT_COLLECTION = "annual_reports"
QUARTER_REPORT_COLLECTION = "quarter_reports"
SEC_REPORT_COLLECTION = "sec_reports"
NEWS_COLLECTION = "news_articles"   
PRICE_COLLECTION = "price_data" 
EARNING_CALL_COLLECTION = "transcripts"
STOCK_IDEA_COLLECTION = "stock_ideas"
PEER_COLLECTION = "peer_data"

# for test mode
# COMPANY_PERMID_DB = "test_company_permid"
# COMPANY_TICKER_DATA = "test_company_ticker"
# SEC_REPORT_COLLECTION = "test_sec_reports"
# NEWS_COLLECTION = "test_news"
# PRICE_COLLECTION = "test_price_data" 
# EARNING_CALL_COLLECTION = "test_transcripts"
# STOCK_IDEA_COLLECTION = "test_stock_ideas"
# PEER_COLLECTION = "test_peer_data"
