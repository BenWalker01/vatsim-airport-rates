import requests
import argparse
from datetime import datetime, timedelta
from datetime import datetime as dt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    print("Error: API_KEY not found in .env file")
    exit(1)

# Configuration variables
OUTPUT_FILE = "hist_rates.csv"
DEFAULT_AIRPORT = "egkk"
DEFAULT_START_DATE = datetime.now().strftime("%Y-%m-%d")
DEFAULT_START_TIME = "00:00"
DEFAULT_END_DATE = datetime.now().strftime("%Y-%m-%d")
DEFAULT_END_TIME = datetime.now().strftime("%H:%M")

# API Configuration
API_BASE_URL_ARRIVALS = "https://api.statsim.net/api/Flights/IcaoDestination"
API_BASE_URL_DEPARTURES = "https://api.statsim.net/api/Flights/IcaoOrigin"
HEADERS = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}

# Parse command line arguments if provided
parser = argparse.ArgumentParser(
    description='Calculate historic rates for an airport')
parser.add_argument('--airport', type=str,
                    default=DEFAULT_AIRPORT, help='ICAO airport code')
parser.add_argument('--start-date', type=str,
                    default=DEFAULT_START_DATE, help='Start date (YYYY-MM-DD)')
parser.add_argument('--start-time', type=str,
                    default=DEFAULT_START_TIME, help='Start time (HH:MM)')
parser.add_argument('--end-date', type=str,
                    default=DEFAULT_END_DATE, help='End date (YYYY-MM-DD)')
parser.add_argument('--end-time', type=str,
                    default=DEFAULT_END_TIME, help='End time (HH:MM)')
parser.add_argument('--output', type=str, default=OUTPUT_FILE,
                    help='Output CSV file name')
args = parser.parse_args()

# Initialize lists to store data
timestamps = []
dep_rates = []
hour_dep_rates = []
arr_rates = []
hour_arr_rates = []

airport = args.airport.upper()
start_datetime = f"{args.start_date}T{args.start_time}:00Z"
end_datetime = f"{args.end_date}T{args.end_time}:00Z"

# Build API query
params = {
    "icao": airport,
    "from": start_datetime,
    "to": end_datetime
}

print(f"Fetching data for {airport} from {start_datetime} to {end_datetime}")

print("Fetching arrival data...")
arrival_response = requests.get(API_BASE_URL_ARRIVALS, params=params, headers=HEADERS)

if arrival_response.status_code == 401:
    print("Error: Unauthorized - API key may be invalid")
    exit(1)
elif arrival_response.status_code == 400:
    print("Error: Bad Request - Check your parameters")
    print(f"Request URL: {arrival_response.url}")
    print(f"Response body: {arrival_response.text}")
    exit(1)
elif arrival_response.status_code != 200:
    print(f"Error: API returned status code {arrival_response.status_code}")
    print(f"Response: {arrival_response.text}")
    exit(1)

if not arrival_response.text or arrival_response.text.strip() == "":
    print("Error: API returned an empty response")
    exit(1)

try:
    arrival_data = arrival_response.json()
except requests.exceptions.JSONDecodeError as e:
    print(f"Error: Failed to parse JSON response: {e}")
    print(f"Status Code: {arrival_response.status_code}")
    print(f"Response text (first 1000 chars):\n{arrival_response.text[:1000]}")
    exit(1)

print(f"API returned {len(arrival_data)} flights arriving at {airport}")

print("Fetching departure data...")
departure_response = requests.get(API_BASE_URL_DEPARTURES, params=params, headers=HEADERS)

if departure_response.status_code != 200:
    print(f"Error: Departure data fetch failed with status code {departure_response.status_code}")
    departure_data = []
else:
    try:
        departure_data = departure_response.json()
    except requests.exceptions.JSONDecodeError:
        print("Warning: Failed to parse departure data, continuing with empty departures")
        departure_data = []

print(f"API returned {len(departure_data)} flights departing from {airport}")

import json
with open("api_response.json", "w") as f:
    json.dump({"arrivals": arrival_data, "departures": departure_data}, f, indent=2)
print(f"JSON responses saved to api_response.json")

def extract_timestamps_from_flights(flights, use_field='arrived'):
    """Extract and sort timestamps from flight data"""
    timestamps = []
    for flight in flights:
        if isinstance(flight, dict):
            ts = flight.get(use_field)
            if ts:
                try:
                    # Parse ISO format timestamp
                    dt_obj = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    timestamps.append(int(dt_obj.timestamp()))
                except (ValueError, AttributeError, TypeError):
                    pass
    return sorted(list(set(timestamps)))

arrival_timestamps = extract_timestamps_from_flights(arrival_data, use_field='arrived')
departure_timestamps = extract_timestamps_from_flights(departure_data, use_field='departed')
all_timestamps = sorted(list(set(arrival_timestamps + departure_timestamps)))

if not all_timestamps:
    print("Error: Could not extract any valid timestamps from flight data")
    exit(1)

print(f"Found {len(all_timestamps)} unique timestamps")

def calculate_rates(flights, timestamps, use_field='arrived'):
    """Calculate rolling 15-min and hourly rates for flights"""
    rolling_15min = []  # Rate per hour, calculated from 15-min windows
    hourly = []  # Actual hourly rate
    
    def get_flight_timestamp(flight):
        """Extract timestamp from flight object"""
        ts = flight.get(use_field)
        if ts:
            try:
                dt_obj = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return int(dt_obj.timestamp())
            except (ValueError, AttributeError, TypeError):
                return None
        return None
    
    for ts in timestamps:
        window_start = ts - 900
        count_15min = sum(1 for flight in flights
                         if isinstance(flight, dict)
                         and (flight_ts := get_flight_timestamp(flight))
                         and window_start <= flight_ts <= ts)
        rolling_15min.append(int(count_15min * 4))
        
        window_start_hour = ts - 3600
        count_1hour = sum(1 for flight in flights
                         if isinstance(flight, dict)
                         and (flight_ts := get_flight_timestamp(flight))
                         and window_start_hour <= flight_ts <= ts)
        hourly.append(count_1hour)
    
    return rolling_15min, hourly

arrival_rolling_15min, arrival_hourly = calculate_rates(arrival_data, all_timestamps, use_field='arrived')
departure_rolling_15min, departure_hourly = calculate_rates(departure_data, all_timestamps, use_field='departed')

output_file = args.output
with open(output_file, 'w') as f:
    ts_row = "timestamps," + ",".join(str(ts) for ts in all_timestamps)
    f.write(ts_row + "\n")
    
    dep_rolling_row = "rolling_departure_rates," + ",".join(str(rate) for rate in departure_rolling_15min)
    f.write(dep_rolling_row + "\n")
    
    dep_actual_row = "actual_departure_rates," + ",".join(str(rate) for rate in departure_hourly)
    f.write(dep_actual_row + "\n")
    
    arr_rolling_row = "rolling_arrival_rates," + ",".join(str(rate) for rate in arrival_rolling_15min)
    f.write(arr_rolling_row + "\n")
    
    arr_actual_row = "actual_arrival_rates," + ",".join(str(rate) for rate in arrival_hourly)
    f.write(arr_actual_row + "\n")

print(f"Data exported to {output_file}")

