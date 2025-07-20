import os
import sys
from datetime import datetime
from airflow.models import Variable
# Temporarily modify sys.path to include the plugins directory for local testing
sys.path.append('/data/seanchoi/airflow/plugins')
for path in sys.path:
    print(path)
    
# Debugging: Print the current working directory
print("Current Working Directory:", os.getcwd())

# Debugging: Print the script's directory
print("Script Directory:", os.path.dirname(os.path.abspath(__file__)))

# Import the required modules
try:
    from common.nasdaqAPI_finance_calendars import get_earnings_today, get_earnings_by_date
    print("Import successful!")
except ModuleNotFoundError as e:
    print("ModuleNotFoundError:", e)




# # earning = get_earnings_today()
earnings = get_earnings_by_date(datetime(2025, 7, 10, 0, 0))


print(earnings['time'].unique())
print(earnings[earnings['time'] == 'time-not-supplied'])
print(earnings[earnings['time'] == 'after-hours'])
print(earnings[earnings['time'] == 'pre-market'])

# # Define time slots and their corresponding schedules
# schedule_map = {
#     "pre_market": "*/5 11-13 * * *",  # Pre-market: Every 5 minutes from 11:00 AM to 2:00 PM UTC equivalent of 07:00 AM to 10:00 AM ET
#     "after_hours": "*/5 20-22 * * *",  # After-hours: Every 5 minutes from 8:00 PM to 11:00 PM UTC equivalent of 4:00 PM to 7:00 PM ET
# }

# # Fetch the current time slot from Airflow Variables
# time_slot = Variable.get("time_slot", default_var="pre_market")  # Default to pre-market

# # Get the dynamic schedule based on the time slot
# dynamic_schedule = schedule_map.get(time_slot, "*/5 11-13 * * *")  # Default to pre-market


# # For the dockerised image
from datetime import datetime
from plugins.common.nasdaqAPI_finance_calendars import get_earnings_today

def fetch_calls_calendars():
    calls = get_earnings_today()
    # No earnings today such as weekends or holidays
    if calls.empty: 
        # Stop the DAG from running
        # Temp
        print("No earnings today, stopping the DAG.")
        return None
    calls_df = calls[['time']]

    # Return the DataFrame as a dictionary (XComs can only store serializable data)
    return calls_df.to_dict()
    
    # earning_df.to_dict() will returns
    # {
    #     'time': {
    #         'DAL': 'time-not-supplied',
    #         'CAG': 'time-not-supplied',
    #         'LEVI': 'time-not-supplied',
    #         'VIST': 'time-not-supplied',
    #         'PSMT': 'time-not-supplied',
    #         'SMPL': 'time-not-supplied',
    #         'WDFC': 'time-not-supplied',
    #         'ETWO': 'time-not-supplied',
    #         'KALV': 'time-not-supplied'
    #     }
    # }
    
    # (In progress) Let's reorganise the data format later. First of all, input and output checking 

