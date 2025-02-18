from datetime import datetime
import shutil
import os
import sys
import matplotlib.pyplot as plt


def main(inputName):
    # Copy the rates.csv file to a temporary file
    shutil.copy(inputName, f'{inputName[:-4]}_copy.csv')

    # Read the CSV data from the copied file
    timestamps = []
    dep_rates = []
    hour_rates = []

    with open(inputName, "r") as f:
        timestamps, dep_rates, hour_rates = f.read().splitlines()
    timestamps = timestamps.split(",")[1:]
    dep_rates = dep_rates.split(",")[1:]
    hour_rates = hour_rates.split(",")[1:]
        
    # Filter out empty strings and convert timestamps to datetime objects
    timestamps = [float(ts) for ts in timestamps if ts]

    start_time = timestamps[0]
    timestamps = [ts - start_time for ts in timestamps]

    # Convert dep_rates and hour_rates to float, filtering out empty strings
    dep_rates = [int(float(rate)) for rate in dep_rates if rate]
    hour_rates = [int(rate) for rate in hour_rates if rate]

    # Plot the data
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, dep_rates, label='Rolling 15 min dep rate')
    plt.plot(timestamps, hour_rates, label='Actual Rate')
    plt.xlabel('Time')
    plt.ylabel('Rates')
    plt.title('Arrival Rates Over Time')
    plt.legend()


    plt.savefig(f'{inputName[:-4]}.png')
    # Remove the temporary file
    os.remove(f'{inputName[:-4]}_copy.csv')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 graph.py <name of csv>")
        sys.exit(1)

    inputName = sys.argv[1]
    if not inputName.endswith(".csv"):
        inputName = f"{inputName}.csv"
    main(inputName)