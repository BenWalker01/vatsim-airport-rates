const MAX_RANGE_MS = 31 * 24 * 60 * 60 * 1000;
const STATSIM_BASE_URL = "https://api.statsim.net/api/Flights";

function response(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": origin,
      "Vary": "Origin",
    },
  });
}

function allowedOrigin(request, environment) {
  const origin = request.headers.get("Origin");
  return origin && origin === environment.ALLOWED_ORIGIN ? origin : null;
}

function timestamps(flights, field) {
  return flights
    .map((flight) => Date.parse(flight[field]))
    .filter(Number.isFinite)
    .sort((left, right) => left - right);
}

function countInWindow(values, timestamp, windowMs) {
  return values.filter((value) => value >= timestamp - windowMs && value <= timestamp).length;
}

function calculateSamples(arrivals, departures) {
  const arrivalTimes = timestamps(arrivals, "arrived");
  const departureTimes = timestamps(departures, "departed");
  const allTimes = [...new Set([...arrivalTimes, ...departureTimes])].sort((left, right) => left - right);
  return allTimes.map((time) => ({
    time,
    rollingDepartures: countInWindow(departureTimes, time, 15 * 60 * 1000) * 4,
    hourlyDepartures: countInWindow(departureTimes, time, 60 * 60 * 1000),
    rollingArrivals: countInWindow(arrivalTimes, time, 15 * 60 * 1000) * 4,
    hourlyArrivals: countInWindow(arrivalTimes, time, 60 * 60 * 1000),
  }));
}

async function fetchFlights(endpoint, icao, from, to, apiKey) {
  const url = new URL(`${STATSIM_BASE_URL}/${endpoint}`);
  url.search = new URLSearchParams({ icao, from, to });
  const result = await fetch(url, { headers: { "Accept": "application/json", "X-API-Key": apiKey } });
  if (!result.ok) throw new Error(`Statsim ${endpoint} request failed with ${result.status}.`);
  const data = await result.json();
  return Array.isArray(data) ? data : [];
}

export default {
  async fetch(request, environment) {
    const origin = allowedOrigin(request, environment);
    if (!origin) return new Response("Forbidden", { status: 403 });
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "GET", "Vary": "Origin" } });
    }
    if (request.method !== "GET") return response({ error: "Method not allowed." }, 405, origin);
    if (!environment.STATSIM_API_KEY) return response({ error: "Worker API key is not configured." }, 500, origin);

    const url = new URL(request.url);
    const icao = (url.searchParams.get("icao") || "").toUpperCase();
    const from = url.searchParams.get("from");
    const to = url.searchParams.get("to");
    const fromTime = Date.parse(from);
    const toTime = Date.parse(to);
    if (!/^[A-Z]{4}$/.test(icao) || !Number.isFinite(fromTime) || !Number.isFinite(toTime)
      || toTime <= fromTime || toTime - fromTime > MAX_RANGE_MS) {
      return response({ error: "Use a four-letter ICAO and a date range of at most 31 days." }, 400, origin);
    }
    try {
      const [arrivals, departures] = await Promise.all([
        fetchFlights("IcaoDestination", icao, from, to, environment.STATSIM_API_KEY),
        fetchFlights("IcaoOrigin", icao, from, to, environment.STATSIM_API_KEY),
      ]);
      return response({ samples: calculateSamples(arrivals, departures) }, 200, origin);
    } catch (error) {
      return response({ error: error.message }, 502, origin);
    }
  },
};
