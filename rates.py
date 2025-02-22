import json
import requests
import time
from shapely.geometry import Point, Polygon
import os
import threading
import logging
import sys
import math

# url = "https://data.vatsim.net/v3/vatsim-data.json"  # regenerates every 15s

# payload = {}
# headers = {
#     'Accept': 'application/json'
# }

HOUR = 3600


# from https://rosettacode.org/wiki/Haversine_formula#Python
def haversine(lat1, lon1, lat2, lon2):
    """Returns distance between to points

    Args:
        lat1 (float):
        lon1 (float):
        lat2 (float):
        lon2 (float):

    Returns:
        float: Distance between 2 points in KM
    """
    R = 6372.8  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dLat / 2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dLon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


class VatsimApiClient:
    def __init__(self, url=None, headers=None, payload=None):
        self.url = url if url else "https://data.vatsim.net/v3/vatsim-data.json"
        self.headers = headers if headers else {'Accept': 'application/json'}
        self.payload = payload if payload else {}

        self.pilots = {}
        self.stop = False
        self.thread = threading.Thread(target=self.update_pilots)
        self.thread.daemon = True
        self.thread.start()

    def update_pilots(self):
        while not self.stop:
            self.get_pilots()
            time.sleep(15)

    def get_pilots(self):
        response = requests.request(
            "GET", self.url, headers=self.headers, data=self.payload)
        self.pilots = response.json().get('pilots', {})


class Airport:
    def __init__(self, boundary, elevation, icao, api_client):
        self.api_client = api_client

        self.boundary = Polygon(boundary)
        self.elevation = elevation
        self.icao = icao
        minx, miny, maxx, maxy = self.boundary.bounds
        self.midpoint = Point(
            ((minx + maxx) / 2, (miny + maxy) / 2))

        self.on_ground = set()
        self.departed = set()
        self.dep_hour_track = set()

        self.on_approach = set()
        self.arrived = set()
        self.arr_hour_track = set()

        self.rolling_rate = 15 * 60  # 15 mins

        self.filename = f"{self.icao}_{time.strftime('%H%M%S_%Y%m%d')}_rates.csv"
        self.stop = False

        with open(self.filename, "w") as f:
            f.write(f"0,\n0,\n0,\n0,\n0,")

        if os.path.exists(f"{self.icao}.log"):
            os.remove(f"{self.icao}.log")

        logging.basicConfig(
            filename=f"{self.icao}.log", level=logging.INFO)

    def get_pilots(self):
        return self.api_client.pilots

    def process_data(self):
        while not self.stop:
            start = time.time()
            data = self.get_pilots()
            currently_on_ground = set()
            currently_on_approach = set()

            for pilot in data:
                callsign = pilot.get('callsign')
                lat = pilot.get('latitude', None)
                lon = pilot.get('longitude', None)
                alt = pilot.get('altitude', None)
                plan = pilot.get('flight_plan', None)

                if plan:
                    dep = plan.get('departure', None)
                    arr = plan.get('arrival', None)
                    rules = plan.get('flight_rules', None)

                    if lat and lon and rules == "I":
                        point = Point(lat, lon)

                        if self.boundary.contains(point) and alt < self.elevation + 200 and dep == self.icao:
                            currently_on_ground.add(callsign)
                            logging.info(
                                f"Pilot {callsign} is on the ground at {self.icao}")

                        elif haversine(point.x, point.y, self.midpoint.x, self.midpoint.y) <= 50 and arr == self.icao and not self.boundary.contains(point) and alt > self.elevation + 200:
                            currently_on_approach.add(callsign)
                            logging.info(
                                f"Pilot {callsign} is within 50 KM of {self.icao}")

            for cs in self.on_ground:
                if cs not in currently_on_ground:  # i.e they left
                    for pilot in data:
                        callsign = pilot.get('callsign', None)
                        if callsign == cs:  # still connected
                            departure_time = time.time()
                            self.departed.add((cs, departure_time))
                            self.dep_hour_track.add((cs, departure_time))
                            logging.info(
                                f"{callsign} has departed from {self.icao}")
                            break

            self.on_ground = currently_on_ground
            self.departed = {(plane, tot) for plane, tot in self.departed if time.time(
            ) - tot <= self.rolling_rate}
            self.dep_hour_track = {
                (plane, tot) for plane, tot in self.dep_hour_track if time.time() - tot <= HOUR}

            for cs in self.on_approach:
                if cs not in currently_on_approach:
                    for pilot in data:
                        callsign = pilot.get('callsign', None)
                        if callsign == cs:
                            arrival_time = time.time()
                            self.arrived.add((cs, arrival_time))
                            self.arr_hour_track.add((cs, arrival_time))
                            logging.info(
                                f"{callsign} has arrived at {self.icao}")
                            break

            self.on_approach = currently_on_approach
            self.arrived = {(plane, tot) for plane, tot in self.arrived if time.time(
            ) - tot <= self.rolling_rate}
            self.arr_hour_track = {
                (plane, tot) for plane, tot, in self.arr_hour_track if time.time() - tot <= HOUR}

            estimated_departure_rate = len(
                self.departed) * (HOUR / self.rolling_rate)
            estimated_arrival_rate = len(
                self.arrived) * (HOUR / self.rolling_rate)

            logging.info(
                f"{self.icao} estimated departure rate: {estimated_departure_rate} per hour")
            logging.info(
                f"{self.icao} Current actual departure rate {len(self.dep_hour_track)} per hour")
            logging.info(
                f"{self.icao} estimated arrival rate: {estimated_arrival_rate} per hour")
            logging.info(
                f"{self.icao} Current actual arrival rate {len(self.arr_hour_track)} per hour")

            with open(self.filename, "r")as f:
                timestamps, rolling_dep_rate, actual_dep_rate, rolling_arr_rate, actual_arr_rate = f.read().splitlines()
                timestamps += f"{int(time.time())},"
                rolling_dep_rate += f"{estimated_departure_rate},"
                actual_dep_rate += f"{len(self.dep_hour_track)},"
                rolling_arr_rate += f"{estimated_arrival_rate},"
                actual_arr_rate += f"{len(self.arr_hour_track)},"

                lines = f"{timestamps}\n{rolling_dep_rate}\n{actual_dep_rate}\n{rolling_arr_rate}\n{actual_arr_rate}"

            with open(self.filename, "w")as f:
                f.write(lines)

            diff = time.time() - start
            logging.info(f"{self.icao} loop took {diff}s")
            time.sleep(max(15-diff, 0))


if __name__ == "__main__":
    with open("boundingBoxes.json")as f:
        airport_data = json.load(f)

    tracking = {}

    os.system('cls' if os.name == 'nt' else 'clear')

    api_client = VatsimApiClient()

    while True:
        if tracking:
            print(f"Tracking {', '.join(list(tracking))}")
        airport = input("Enter airport ICAO to track\n> ")

        if airport.lower() in ["exit", "stop", "quit"]:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"Stopping processes:")
            for runningThread, activeAirport in tracking.values():
                print(f"Stopping {activeAirport.icao}")
                activeAirport.stop = True
                runningThread.join()
                print(f"Stopped {activeAirport.icao}")
            print(f"Stopping api client")
            api_client.stop = True
            api_client.thread.join()
            sys.exit(0)

        elif airport.upper() in tracking:
            tracking[airport.upper()][1].stop = True
            tracking[airport.upper()][0].join()
            tracking.pop(airport.upper())
            print(f"Stopped tracking {airport.upper()} ")

        elif airport.upper() in airport_data.keys():
            bbox = airport_data.get(airport.upper()).get('boundingBox')
            elev = airport_data.get(airport.upper()).get('elevation')
            airport_tracker = Airport(bbox, elev, airport.upper(), api_client)

            thread = threading.Thread(target=airport_tracker.process_data)
            thread.daemon = True
            thread.start()

            tracking[airport.upper()] = (thread, airport_tracker)
            print(f"Now tracking {airport.upper()}")

        else:
            print("That airport is not in the datafile")

        time.sleep(1)
        os.system('cls' if os.name == 'nt' else 'clear')
