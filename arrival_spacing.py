import requests
import math
import json
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import sys
from shapely.geometry import LineString, Point


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


response = requests.get(
    "https://statsim.net/flights/airport/?icao=egss&period=custom&from=2025-02-22+18%3A00&to=2025-02-22+21%3A30&json=true").json()

arrivals = response.get('arrived', {})

sorted_arrivals = sorted(arrivals, key=lambda x: float(x['arrived']))

callsign_id_arrivals = [(flight.get('callsign'), flight.get(
    'id'), flight.get('arrived')) for flight in sorted_arrivals]

spacing = []
prev_plane = None

with open('boundingBoxes.json') as f:
    ap_data = json.load(f)
    threshold = ap_data.get('EGSS', None).get('threshold', None)

for i, data in enumerate(callsign_id_arrivals[:-1]):
    callsign, id_, arrival_time = data

    current_track = requests.get(
        f"https://statsim.net/flights/flight/?flightid={id_}&json=true").json().get('points', {})

    for j, point in enumerate(current_track[:-1]):
        point1 = point
        point2 = current_track[j+1]

        line = LineString([(point1['latitude'], point1['longitude']),
                          (point2['latitude'], point2['longitude'])])
        threshold_point = Point(threshold[0], threshold[1])

        # Adjust the distance threshold as needed
        if line.distance(threshold_point) < 1 and haversine(point1['latitude'], point1['longitude'], threshold[0], threshold[1]) < 1:
            line_length = haversine(
                point1['latitude'], point1['longitude'], point2['latitude'], point2['longitude'])
            dist_to_end = haversine(
                point1['latitude'], point1['longitude'], threshold[0], threshold[1])
            time_over_threshold = ((point2.get(
                'time') - point1.get('time')) * (dist_to_end / line_length)) + point1.get('time')
            time_over_threshold = int(round(time_over_threshold, 0))
            break

    current_track = requests.get(
        f"https://statsim.net/flights/flight/?flightid={callsign_id_arrivals[i+1][1]}&json=true").json().get('points', {})

    for j, point in enumerate(current_track):
        if float(point.get('time')) > time_over_threshold:
            after = point.get('time')
            before = current_track[j-1].get('time')
            lat1 = point.get('latitude')
            lng1 = point.get('longitude')
            lat2 = current_track[j-1].get('latitude')
            lng2 = current_track[j-1].get('longitude')

            lat = lat1 + (lat2 - lat1) * \
                ((time_over_threshold - before) / (after - before))
            lng = lng1 + (lng2 - lng1) * \
                ((time_over_threshold - before) / (after - before))

            spacing.append(haversine(lat, lng, threshold[0], threshold[1]))
            print(
                f"{callsign} {id_} landed, the next plane is {callsign_id_arrivals[i+1][0]} {callsign_id_arrivals[i+1][1]}")
            print(
                f"The trailing plane at {lat},{lng}, with spacing of {haversine(lat, lng, threshold[0], threshold[1])}")
            break


timestamps = [datetime.fromtimestamp(float(ts))
              for _, _, ts in callsign_id_arrivals]
callsigns = [cs for cs, _, _ in callsign_id_arrivals]
# spacing = [s if s <= 15 else 0 for s in spacing]

print(len(spacing))
print(len(callsigns[:-1]))

# Calculate the moving average
window_size = 5
moving_avg = np.convolve(spacing, np.ones(
    window_size)/window_size, mode='valid')
plt.figure(figsize=(12, 6))
plt.bar(callsigns[:-1], spacing,
        label="Final approach spacing")
plt.plot(callsigns[window_size-1:-1], moving_avg,
         label="Trend (Moving Average)", color='orange', linestyle='--')

plt.axhline(y=6, color='red', linestyle='-')
plt.axhline(y=4, color='green', linestyle='-')

plt.ylim(0, 20)

plt.xlabel('Time')
plt.ylabel('Miles in Trail')
plt.title(
    f'Arrival Spacing - average {round(sum(spacing)/len(spacing), 2)}NM in trail')
plt.legend()
plt.xticks(rotation=90)
plt.gcf().subplots_adjust(bottom=0.3)
plt.savefig(f'arrival_spacing.png')
