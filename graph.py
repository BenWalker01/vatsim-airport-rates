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
    rolling_departure_rates = []
    actual_departure_rates = []
    rolling_arrival_rates = []
    actual_arrival_rates = []

    with open(inputName, "r") as f:
        timestamps, rolling_departure_rates, actual_departure_rates, rolling_arrival_rates, actual_arrival_rates = f.read().splitlines()
    timestamps = timestamps.split(",")[1:]
    rolling_departure_rates = rolling_departure_rates.split(",")[1:]
    actual_departure_rates = actual_departure_rates.split(",")[1:]
    rolling_arrival_rates = rolling_arrival_rates.split(",")[1:]
    actual_arrival_rates = actual_arrival_rates.split(",")[1:]

    timestamps = [float(ts) for ts in timestamps if ts]

    # Convert timestamps to datetime objects
    timestamps = [datetime.fromtimestamp(ts) for ts in timestamps]

    rolling_departure_rates = [int(float(rate))
                               for rate in rolling_departure_rates if rate]
    actual_departure_rates = [int(rate)
                              for rate in actual_departure_rates if rate]

    rolling_arrival_rates = [int(float(rate))
                             for rate in rolling_arrival_rates if rate]
    actual_arrival_rates = [int(float(rate))
                            for rate in actual_arrival_rates if rate]

    rolling_runway_util = [dep + arr
                           for dep, arr in zip(rolling_departure_rates, rolling_arrival_rates)]
    actual_runway_util = [dep + arr
                          for dep, arr in zip(actual_departure_rates, actual_arrival_rates)]

    # Plot departure rates
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, rolling_departure_rates,
             label='Rolling 15 min dep rate')
    plt.plot(timestamps, actual_departure_rates, label='Actual Rate')
    plt.xlabel('Time')
    plt.ylabel('Rate per hour')
    plt.title('Departure Rates Over Time')
    plt.legend()
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.savefig(f'{inputName[:-4]}_departure.png')

    # Plot arrival rates
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, rolling_arrival_rates,
             label='Rolling 15 min arr rate')
    plt.plot(timestamps, actual_arrival_rates, label='Actual Rate')
    plt.xlabel('Time')
    plt.ylabel('Rate per hour')
    plt.title('Arrival Rates Over Time')
    plt.legend()
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.savefig(f'{inputName[:-4]}_arrival.png')

    # Plot runway util
    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, rolling_runway_util,
             label='Rolling 15 min runway utilisation')
    plt.plot(timestamps, actual_runway_util, label='Runway Utilisation')
    plt.xlabel('Time')
    plt.ylabel('Movements Per Hour')
    plt.title('Runway Utilisation')
    plt.legend()
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.savefig(f'{inputName[:-4]}_util.png')

    # Remove the temporary file
    os.remove(f'{inputName[:-4]}_copy.csv')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 graph.py <name of csv>")
        sys.exit(1)

    inputName = sys.argv[1]
    if not inputName.endswith(".csv"):
        inputName = f"{inputName}.csv"
    main(inputName)
