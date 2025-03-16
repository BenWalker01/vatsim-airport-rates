import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np

icao = "egcc"
start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 3, 15)

current_date = start_date

# Initialize arrays to store counts for each hour of each day
hourly_departed_counts = np.zeros(24 * 7)
hourly_arrived_counts = np.zeros(24 * 7)
hourly_counts = np.zeros(24 * 7)

while current_date < end_date:
    day_of_week = current_date.weekday()  # Monday is 0 and Sunday is 6
    print(current_date.strftime('%Y-%m-%d'))
    for hour in range(24):
        from_time = current_date.replace(hour=hour, minute=0, second=0)
        to_time = from_time + timedelta(hours=1) - timedelta(seconds=1)
        
        req = f"https://statsim.net/flights/airport/?icao={icao}&period=custom&from={from_time.strftime('%Y-%m-%d+%H%%3A%M%%3A%S')}&to={to_time.strftime('%Y-%m-%d+%H%%3A%M%%3A%S')}&json=true"
        
        response = requests.get(req).json()
        departed = len(response.get('departed', []))
        arrived = len(response.get('arrived', []))
        
        index = day_of_week * 24 + hour
        hourly_departed_counts[index] += departed
        hourly_arrived_counts[index] += arrived
        hourly_counts[index] += 1
    
    current_date += timedelta(days=1)

# Calculate the average number of flights for each hour of each day
average_departed_counts = hourly_departed_counts / hourly_counts
average_arrived_counts = hourly_arrived_counts / hourly_counts

# Combine movements
average_total_counts = average_departed_counts + average_arrived_counts

# Plotting the data
hours = range(24 * 7)
plt.figure(figsize=(14, 7))

plt.plot(hours, average_total_counts, label='Average Total Movements', marker='o')

plt.xlabel('Hour of the Week')
plt.ylabel('Average Number of Flights')
plt.title(f'Average Hourly Movements at {icao.upper()} for Each Day of the Week')
plt.legend()
plt.grid(True)
plt.xticks(ticks=range(0, 24 * 7, 24), labels=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
plt.tight_layout()

# Save the plot as an image file
plt.savefig('average_hourly_movements_week.png')