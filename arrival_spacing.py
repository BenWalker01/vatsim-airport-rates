import requests, math, json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

# from https://rosettacode.org/wiki/Haversine_formula#Python
def haversine(lat1, lon1, lat2, lon2):
    """Returns distance between to points

    Args:
        lat1 (float):
        lon1 (float):
        lat2 (float):
        lon2 (float):

    Returns:
        float: Distance between 2 points in NM
    """
    R = 6372.8  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat / 2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dLon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c * 0.539957


response = requests.get("https://statsim.net/flights/airport/?icao=egss&period=custom&from=2025-02-22+18%3A00&to=2025-02-22+21%3A30&json=true").json()

arrivals = response.get('arrived', {})

sorted_arrivals = sorted(arrivals, key=lambda x: x['arrived'])

callsign_id_arrivals = [(flight.get('callsign'), flight.get('id'), flight.get('arrived')) for flight in sorted_arrivals]

spacing = []

with open('boundingBoxes.json') as f:
    ap_data = json.load(f)
    threshold = ap_data.get('EGSS', None).get('threshold', None)

for i, data in enumerate(callsign_id_arrivals[:-1]):
    callsign, id_, arrival_time = data
    print(f"{callsign} landed, the next plane is {callsign_id_arrivals[i+1][0]}, with id {callsign_id_arrivals[i+1][1]}")
    next_track = requests.get(f"https://statsim.net/flights/flight/?flightid={callsign_id_arrivals[i+1][1]}&json=true").json().get('points', {})

    point_before_arrival = None
    point_after_arrival = None
    for point in next_track:
        point_time = point.get('time')
        if point_time < arrival_time:
            point_before_arrival = point
        elif point_time > arrival_time and point_after_arrival is None:
            point_after_arrival = point
            break

    if point_before_arrival and point_after_arrival:
        # Interpolate the point at arrival_time
        time_before = point_before_arrival['time']
        time_after = point_after_arrival['time']
        factor = (arrival_time - time_before) / (time_after - time_before)

        interpolated_point = {
            'time': arrival_time,
            'latitude': point_before_arrival['latitude'] + factor * (point_after_arrival['latitude'] - point_before_arrival['latitude']),
            'longitude': point_before_arrival['longitude'] + factor * (point_after_arrival['longitude'] - point_before_arrival['longitude']),
            'altitude': point_before_arrival['altitude'] + factor * (point_after_arrival['altitude'] - point_before_arrival['altitude']),
            'speed': point_before_arrival['speed'] + factor * (point_after_arrival['speed'] - point_before_arrival['speed'])
        }

        print(f"Interpolated point at arrival time {arrival_time}: {interpolated_point}")

        dist = haversine(threshold[0], threshold[1], interpolated_point['latitude'], interpolated_point['longitude'])
        spacing.append(dist)
        print(f"{callsign} had {dist}NM behind at touchdown")

timestamps = [datetime.fromtimestamp(float(ts)) for _, _, ts in callsign_id_arrivals]
callsigns = [cs for cs, _, _ in callsign_id_arrivals]

print(len(spacing))
print(len(callsigns[:-1]))

# Calculate the moving average
window_size = 5
moving_avg = np.convolve(spacing, np.ones(window_size)/window_size, mode='valid')

plt.figure(figsize=(10, 5))
plt.plot(timestamps[:-1], spacing, label="Final approach spacing")
plt.plot(timestamps[window_size-1:-1], moving_avg, label="Trend (Moving Average)", linestyle='--')
plt.xlabel('Time')
plt.ylabel('Miles in Trail')
plt.title('Arrival Spacing')
plt.legend()
plt.savefig(f'arrival_spacing.png')