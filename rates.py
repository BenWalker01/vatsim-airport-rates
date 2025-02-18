import requests,time
from shapely.geometry import Point, Polygon


class Airport:
	def __init__(self,boundry, elevation,icao):
		self.boundry = Polygon(boundry)
		self.elevation = elevation
		self.icao = icao

airport = [(50.074935640323474, 8.44810178631773),(49.97464929980614, 8.48257453416403),(49.9961902982015, 8.664163374453615),(50.08132315919908, 8.631389988683265)]

#EGKK
#airport = [(51.13719270370898, -0.21951900613886854),(51.141721140088784, -0.14012682199274115),(51.1792900203234, -0.153118270307562),(51.16897294200857, -0.22919041766212397)]
#EGPH
#airport = [(55.971760870855405, -3.3355042299469266),(55.93283621469401, -3.3263203472236804),(55.934951645546896, -3.3925816353185465),(55.96210544001433, -3.406829529098473)]
#EGCC
#airport = [(53.37328989679097, -2.3346548753120744),(53.32256468988526, -2.3196255728380852),(53.326592705048924, -2.2386985595166053),(53.39006997975631, -2.2504522447847246)]
airport_poly = Polygon(airport)
url = "https://data.vatsim.net/v3/vatsim-data.json" # regenerates every 15s

payload={}
headers = {
  'Accept': 'application/json'
}

on_ground = set()
departed = set()
hour_track = set()
global_start = time.time()
rolling_rate = 15 
rolling_rate *= 60 
HOUR = 3600


with open("rates.csv","w")as f:
	f.write(f"0,\n0,\n0,")
while True:
	start = time.time()
	response = requests.request("GET", url, headers=headers, data=payload)

	#print(response.text)
	data = response.json()

	pilots = data.get('pilots', [])
	currently_on_ground = set()
	for pilot in pilots:
		callsign = pilot.get('callsign')
		lat = pilot.get('latitude', None)
		lon = pilot.get('longitude', None)
		alt = pilot.get('altitude', None)
		plan = pilot.get('flight_plan', None)
		if plan:
			dep = plan.get('departure', None)
			rules = plan.get('flight_rules')
		if lat is not None and lon is not None and rules is not None and dep is not None:
			point = Point(lat, lon)
		if airport_poly.contains(point) and alt < 500 and dep == "EDDF" and rules == "I":
			currently_on_ground.add(callsign)
			print(f"Pilot {callsign} is within the airport polygon.")

	for cs in on_ground:
		if cs not in currently_on_ground:
			for pilot in pilots:
				callsign = pilot.get('callsign') # TODO check alt + speed?
				if callsign == cs: # still connected
					dep_time = time.time()
					departed.add((cs,dep_time))
					hour_track.add((cs,dep_time))
					print(f"{callsign} has departed!")
					break
	on_ground = currently_on_ground

	hour_track = {(plane, tot) for plane, tot in hour_track if end - tot <= HOUR}
	departed = {(plane, tot) for plane, tot in departed if end - tot <= rolling_rate}

	departure_rate_per_hour = len(departed) * HOUR / rolling_rate
	print(f"Corrected Departure rate: {departure_rate_per_hour:.2f} per hour")
	print(f"Actual Departure Rate {len(hour_track)}")

	with open("rates.csv", "r")as f:
		timestamps,dep_rates,hour_rates = f.read().splitlines()
	timestamps += f"{time.time()},"
	dep_rates += f"{departure_rate_per_hour},"
	hour_rates += f"{len(hour_track)},"
	
	lines = f"{timestamps}\n{dep_rates}\n{hour_rates}"


	
	with open("rates.csv","w")as f:
		f.write(lines)



	end = time.time()
	diff = end - start
	print(f"Loop took {diff}")
	time.sleep(max((15 - diff),0))

		
