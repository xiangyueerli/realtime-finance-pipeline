
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Date

Base = declarative_base()

class FileMetadata(Base):
    """
    Stores robust metadata about each file:
        - id: unique identifier (primary key)
        - ticker: Stock ticker symbol
        - download_date: Date when the file was downloaded
        - status: Status of the download (e.g., pending, completed, failed)
        - is_deleted: True if no longer valid on disk
    """
    __abstract__ = True # Mark this class as abstract (no table will be created for it)
    
    id = Column(String, primary_key=True, autoincrement=True)  # Unique identifier for each record
    ticker = Column(String, nullable=False)                    # Stock ticker symbol
    download_date = Column(Date, nullable=False)               # Date when the file was downloaded
    recent_update_date = Column(DateTime, nullable=True)  # Date of the most recent update
    status = Column(String, nullable=False, default='pending') # Status of the download (e.g., pending, completed, failed)
    is_deleted = Column(Boolean, default=False)                # True if the file is no longer valid
    
class CallsMetadata(FileMetadata):
    """
    Metadata for Call files, inheriting from FileMetadata.
    """
    __tablename__ = 'calls_metadata'  # Table name for Call metadata
    
class SECMetadata(FileMetadata):
    """
    Metadata for SEC filings, inheriting from FileMetadata.
    """
    __tablename__ = 'sec_metadata'  # Table name for SEC metadata
    filing_type = Column(String, nullable=False)  # Type of SEC filing (e.g., 10-K, 10-Q)
    
class NewsMetadata(FileMetadata):
    """
    Metadata for News files, inheriting from FileMetadata.
    """
    __tablename__ = 'news_metadata'  # Table name for News metadata
    source = Column(String, nullable=False)  # Source of the news (e.g., Bloomberg, Reuters)
    