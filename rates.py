import json
import requests
import time
from shapely.geometry import Point, Polygon
import os
import threading

url = "https://data.vatsim.net/v3/vatsim-data.json"  # regenerates every 15s

payload = {}
headers = {
    'Accept': 'application/json'
}

HOUR = 3600


class Airport:
    def __init__(self, boundary, elevation, icao):
        self.boundary = Polygon(boundary)
        self.elevation = elevation
        self.icao = icao
        self.on_ground = set()
        self.departed = set()
        self.hour_track = set()
        self.global_start = time.time()
        self.rolling_rate = 15
        self.rolling_rate *= 60

        self.filename = f"{time.time()}_{self.icao}_departure_rate.csv"
        self.stop = False

        with open(self.filename, "w") as f:
            f.write(f"0,\n0,\n0,")

    def get_pilots(self):
        response = requests.request(
            "GET", url, headers=headers, data=payload)

        return response.json().get('pilots', [])

    def process_data(self):
        while not self.stop:
            start = time.time()
            data = self.get_pilots()
            currently_on_ground = set()

            for pilot in data:
                callsign = pilot.get('callsign')
                lat = pilot.get('latitude', None)
                lon = pilot.get('longitude', None)
                alt = pilot.get('altitude', None)
                plan = pilot.get('flight_plan', None)

                if plan:
                    dep = plan.get('departure', None)
                    rules = plan.get('flight_rules', None)
                    if lat and lon and rules == "I" and dep == self.icao:
                        point = Point(lat, lon)
                        if self.boundary.contains(point) and alt < self.elevation:
                            currently_on_ground.add(callsign)
                            print(
                                f"Pilot {callsign} is on the ground at {self.icao}")

            for cs in self.on_ground:
                if cs not in currently_on_ground:  # i.e they left
                    for pilot in data:
                        callsign = pilot.get('callsign', None)
                        if callsign == cs:  # still connected
                            departure_time = time.time()
                            self.departed.add((cs, departure_time))
                            self.hour_track.add((cs, departure_time))
                            print(f"{callsign} has departed from {self.icao}")
                            break

            self.on_ground = currently_on_ground
            self.departed = {(plane, tot) for plane, tot in self.departed if time.time(
            ) - tot <= self.rolling_rate}
            self.hour_track = {
                (plane, tot) for plane, tot in self.hour_track if time.time() - tot <= HOUR}

            estimated_rate = len(self.departed) * (HOUR / self.rolling_rate)
            print(f"{self.icao} estimated departure rate: {estimated_rate} per hour")
            print(
                f"{self.icao} Current actual departure rate {len(self.hour_track)} per hour")

            with open(self.filename, "r")as f:
                timestamps, dep_rates, hour_rates = f.read().splitlines()
                timestamps += f"{int(time.time())},"
                dep_rates += f"{estimated_rate},"
                hour_rates += f"{len(self.hour_track)},"

                lines = f"{timestamps}\n{dep_rates}\n{hour_rates}"

            with open(self.filename, "w")as f:
                f.write(lines)

            diff = time.time() - start
            print(f"{self.icao} loop took {diff}s")
            time.sleep(max(15-diff, 0))


if __name__ == "__main__":
    with open("boundingBoxes.json")as f:
        airport_data = json.load(f)

    tracking = {}

    os.system('cls' if os.name == 'nt' else 'clear')

    while True:
        if tracking:
            print(f"Tracking {', '.join(list(tracking))}")
        airport = input("Enter airport ICAO to track\n> ")
        if airport.upper() in tracking:
            tracking[airport.upper()][1].stop = True
            tracking[airport.upper()][0].join()
            tracking.pop(airport.upper())
            print(f"Stopped tracking {airport.upper()} ")

        elif airport.upper() in airport_data.keys():
            bbox = airport_data.get(airport.upper()).get('boundingBox')
            elev = airport_data.get(airport.upper()).get('elevation')
            airport_tracker = Airport(bbox, elev, airport.upper())

            thread = threading.Thread(target=airport_tracker.process_data)
            thread.daemon = True
            thread.start()

            tracking[airport.upper()] = (thread, airport_tracker)
            print(f"Now tracking {airport}")

        else:
            print("That airport is not in the datafile")

        time.sleep(1)
        os.system('cls' if os.name == 'nt' else 'clear')
