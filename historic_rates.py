import requests
import argparse
from datetime import datetime

# Configuration variables
OUTPUT_FILE = "hist_rates.csv"
DEFAULT_AIRPORT = "egkk"
DEFAULT_START_DATE = datetime.now().strftime("%Y-%m-%d")
DEFAULT_START_TIME = "00:00"
DEFAULT_END_DATE = datetime.now().strftime("%Y-%m-%d")
DEFAULT_END_TIME = datetime.now().strftime("%H:%M")

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

# Initialize output file
with open(args.output, "w")as f:
    f.write(f"0,\n0,\n0,\n0,\n0,")

# Set up request parameters
airport = args.airport
start_time = f"{args.start_date}+{args.start_time.replace(':', '%3A')}"
end_time = f"{args.end_date}+{args.end_time.replace(':', '%3A')}"

url = f"https://statsim.net/flights/airport/?icao={airport}&period=custom&from={start_time}&to={end_time}&json=true"
print(url)
# Get data from statsim.net
response = requests.get(url)


deps = sorted([plane['departed'] for plane in response.json().get('departed')])
arrs = sorted([plane['arrived'] for plane in response.json().get('arrived')])

# Configuration for time intervals
HOUR_WINDOW = 60 * 60  # 1 hour in seconds
ROLLING_WINDOW = 15 * 60  # 15 minutes in seconds
TIME_INCREMENT = 15  # Time increment in minutes

timespan = max(deps[-1] - deps[0], arrs[-1] - arrs[0]) if deps and arrs else 0
if not timespan:
    print("No flights found in the specified time range")
    exit(1)

current_time = deps[0] if deps else 0
hour_dep_rate = set()
hour_arr_rate = set()
rolling_dep_rate = set()
rolling_arr_rate = set()
for i in range(timespan//TIME_INCREMENT + 1):
    if deps and deps[0] <= current_time:  # plane has departed
        hour_dep_rate.add(deps[0])
        rolling_dep_rate.add(deps[0])
        deps.pop(0)

    if arrs and arrs[0] <= current_time:
        hour_arr_rate.add(arrs[0])
        rolling_arr_rate.add(arrs[0])
        arrs.pop(0)

    hour_dep_rate = {
        tot for tot in hour_dep_rate if current_time - tot < HOUR_WINDOW}
    rolling_dep_rate = {
        tot for tot in rolling_dep_rate if current_time - tot < ROLLING_WINDOW}

    hour_arr_rate = {
        tot for tot in hour_arr_rate if current_time - tot < HOUR_WINDOW}
    rolling_arr_rate = {
        tot for tot in rolling_arr_rate if current_time - tot < ROLLING_WINDOW}

    current_time += 15

    with open(args.output, "r")as f:
        timestamps, dep_rates, hour_dep_rates, arr_rates, hour_arr_rates = f.read().splitlines()
    timestamps += f"{current_time},"
    dep_rates += f"{len(rolling_dep_rate)*4},"
    hour_dep_rates += f"{len(hour_dep_rate)},"
    arr_rates += f"{len(rolling_arr_rate)*4},"
    hour_arr_rates += f"{len(hour_arr_rate)},"

    lines = f"{timestamps}\n{dep_rates}\n{hour_dep_rates}\n{arr_rates}\n{hour_arr_rates}"

    with open(args.output, "w")as f:
        f.write(lines)
