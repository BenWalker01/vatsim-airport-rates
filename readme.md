# Vatsim Rates Tool

Simple tool to measure the arrival and departure rates at airports on vatsim.

## Usage

Run `rates.py`

When prompted enter the ICAO of the airports you want to track
```
Enter airport ICAO to track
> 
```

Note, only airports defined in [boundingBoxes.json](boundingBoxes.json) can be used

To plot the data run `graph.py` and pass the csv file as an argument, e.g:

`python3 graph.py EGSS_133538_20250222_rates.csv`

You can plot the data at any time, even while `rates.py` is running

To stop `rates.py` type "stop" or "exit", and it will shut down.