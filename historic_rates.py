import requests

with open("rates.csv","w")as f:
	f.write(f"0,\n0,\n0,")

response = requests.get("https://statsim.net/flights/airport/?icao=egph&period=custom&from=2025-01-26+11%3A00&to=2025-01-26+22%3A00&json=true")


deps = sorted([plane['departed'] for plane in response.json().get('departed')])

timespan = deps[-1] - deps[0]

current_time = deps[0]
hour_rate = set()
rolling_rate = set()
for i in range(timespan//15 + 1):
	if deps[0] <= current_time: # plen has departed
		hour_rate.add(deps[0])
		rolling_rate.add(deps[0])
		deps.pop(0)
		
	hour_rate = {tot for tot in hour_rate if current_time - tot < 60*60}
	rolling_rate = {tot for tot in rolling_rate if current_time - tot < 15*60}

	current_time += 15
	
	
	with open("rates.csv", "r")as f:
		timestamps,dep_rates,hour_rates = f.read().splitlines()
	timestamps += f"{current_time},"
	dep_rates += f"{len(rolling_rate)*4},"
	hour_rates += f"{len(hour_rate)},"
	
	lines = f"{timestamps}\n{dep_rates}\n{hour_rates}"


	
	with open("rates.csv","w")as f:
		f.write(lines)


