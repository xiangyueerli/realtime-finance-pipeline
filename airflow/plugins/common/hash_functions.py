import hashlib

# This script provides a function to generate a unique hash ID for various cases.

def generate_hash_id(ticker, date):
    """
    Generate a unique hash ID based on the ticker and date.
    This can be used to identify records uniquely in the database.
    """
    hash_input = f"{ticker}_{date}".encode('utf-8')
    return hashlib.md5(hash_input).hexdigest()