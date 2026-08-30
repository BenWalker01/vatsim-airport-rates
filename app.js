const VATSIM_DATA_URL = "https://data.vatsim.net/v3/vatsim-data.json";
const POLL_INTERVAL_MS = 15_000;
const ROLLING_WINDOW_MS = 15 * 60_000;
const HOUR_MS = 60 * 60_000;
const SESSION_HISTORY_MS = 6 * HOUR_MS;
const STORAGE_KEY = "vatsim-airport-rates-session";

const state = {
  airport: null,
  airports: {},
  trackers: {},
  timer: null,
};

const select = document.querySelector("#airport-select");
const status = document.querySelector("#live-status");
const historicStatus = document.querySelector("#historic-status");
const metricElements = {
  rollingDepartures: document.querySelector("#rolling-departures"),
  hourlyDepartures: document.querySelector("#hourly-departures"),
  rollingArrivals: document.querySelector("#rolling-arrivals"),
  hourlyArrivals: document.querySelector("#hourly-arrivals"),
};

function haversineKm(lat1, lon1, lat2, lon2) {
  const radians = Math.PI / 180;
  const dLat = (lat2 - lat1) * radians;
  const dLon = (lon2 - lon1) * radians;
  const a = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * radians) * Math.cos(lat2 * radians) * Math.sin(dLon / 2) ** 2;
  return 6372.8 * 2 * Math.asin(Math.sqrt(a));
}

function pointInPolygon(lat, lon, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [latI, lonI] = polygon[i];
    const [latJ, lonJ] = polygon[j];
    const intersects = (lonI > lon) !== (lonJ > lon)
      && lat < ((latJ - latI) * (lon - lonI)) / (lonJ - lonI) + latI;
    if (intersects) inside = !inside;
  }
  return inside;
}

function airportMidpoint(boundary) {
  const lats = boundary.map(([lat]) => lat);
  const lons = boundary.map(([, lon]) => lon);
  return {
    lat: (Math.min(...lats) + Math.max(...lats)) / 2,
    lon: (Math.min(...lons) + Math.max(...lons)) / 2,
  };
}

function pruneEvents(events, now) {
  return events.filter((eventTime) => now - eventTime <= HOUR_MS);
}

function calculateRates(tracker, now) {
  tracker.departures = pruneEvents(tracker.departures, now);
  tracker.arrivals = pruneEvents(tracker.arrivals, now);
  const inWindow = (events, windowMs) => events.filter((eventTime) => now - eventTime <= windowMs).length;
  return {
    rollingDepartures: inWindow(tracker.departures, ROLLING_WINDOW_MS) * 4,
    hourlyDepartures: tracker.departures.length,
    rollingArrivals: inWindow(tracker.arrivals, ROLLING_WINDOW_MS) * 4,
    hourlyArrivals: tracker.arrivals.length,
  };
}

function updateMetrics(rates) {
  metricElements.rollingDepartures.textContent = rates.rollingDepartures;
  metricElements.hourlyDepartures.textContent = rates.hourlyDepartures;
  metricElements.rollingArrivals.textContent = rates.rollingArrivals;
  metricElements.hourlyArrivals.textContent = rates.hourlyArrivals;
}

function persist() {
  const savedSession = {
    airport: state.airport,
    trackers: Object.fromEntries(Object.entries(state.trackers).map(([icao, tracker]) => [
      icao,
      {
        onGround: [...tracker.onGround],
        onApproach: [...tracker.onApproach],
        departures: tracker.departures,
        arrivals: tracker.arrivals,
        samples: tracker.samples,
      },
    ])),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedSession));
}

function restore() {
  const savedText = localStorage.getItem(STORAGE_KEY);
  if (!savedText) return false;
  const saved = JSON.parse(savedText);
  if (!saved || typeof saved !== "object") return false;
  Object.entries(saved.trackers || {}).forEach(([icao, tracker]) => {
    if (!state.trackers[icao] || !tracker || typeof tracker !== "object") return;
    state.trackers[icao] = {
      ...state.trackers[icao],
      onGround: new Set(tracker.onGround || []),
      onApproach: new Set(tracker.onApproach || []),
      departures: pruneEvents(tracker.departures || [], Date.now()),
      arrivals: pruneEvents(tracker.arrivals || [], Date.now()),
      samples: (tracker.samples || []).filter((sample) => Date.now() - sample.time <= SESSION_HISTORY_MS),
    };
  });
  if (saved.airport && state.trackers[saved.airport]) select.value = saved.airport;
  showAirport(select.value || null);
  return true;
}

function drawChart(canvas, samples) {
  const context = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#11191b";
  context.fillRect(0, 0, width, height);
  if (samples.length < 2) {
    context.fillStyle = "#9facaa";
    context.font = "16px system-ui";
    context.fillText("Rate data will appear after two updates.", 24, 40);
    return;
  }

  const padding = { top: 25, right: 25, bottom: 55, left: 45 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxRate = Math.max(1, ...samples.flatMap((sample) => [
    sample.rollingDepartures, sample.hourlyDepartures, sample.rollingArrivals, sample.hourlyArrivals,
  ]));
  context.strokeStyle = "#344044";
  context.fillStyle = "#9facaa";
  context.font = "13px system-ui";
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (plotHeight * i) / 4;
    context.beginPath(); context.moveTo(padding.left, y); context.lineTo(width - padding.right, y); context.stroke();
    context.fillText(String(Math.round(maxRate * (4 - i) / 4)), 10, y + 4);
  }
  const timeLabelCount = Math.min(5, samples.length);
  context.textAlign = "center";
  for (let i = 0; i < timeLabelCount; i++) {
    const sampleIndex = Math.round((i * (samples.length - 1)) / (timeLabelCount - 1 || 1));
    const x = padding.left + (sampleIndex * plotWidth) / (samples.length - 1);
    const label = new Date(samples[sampleIndex].time).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    context.fillText(label, x, height - 30);
  }
  context.textAlign = "start";
  const series = [
    ["rollingDepartures", "#75b8b5", "15 min departures"],
    ["hourlyDepartures", "#3c8683", "Hourly departures"],
    ["rollingArrivals", "#e6a93c", "15 min arrivals"],
    ["hourlyArrivals", "#b87527", "Hourly arrivals"],
  ];
  series.forEach(([key, colour, label], index) => {
    context.strokeStyle = colour;
    context.lineWidth = 2;
    context.beginPath();
    samples.forEach((sample, sampleIndex) => {
      const x = padding.left + (sampleIndex * plotWidth) / (samples.length - 1);
      const y = padding.top + plotHeight - (sample[key] / maxRate) * plotHeight;
      if (sampleIndex === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    context.stroke();
    context.fillStyle = colour;
    context.fillRect(padding.left + index * 205, height - 17, 12, 3);
    context.fillText(label, padding.left + 18 + index * 205, height - 12);
  });
}

function processAirport(icao, pilots, connectedCallsigns, now) {
  const tracker = state.trackers[icao];
  const { airport, midpoint } = tracker;
  const currentGround = new Set();
  const currentApproach = new Set();
  pilots.forEach((pilot) => {
    const plan = pilot.flight_plan;
    if (!plan || plan.flight_rules !== "I" || !Number.isFinite(pilot.latitude)
      || !Number.isFinite(pilot.longitude) || !Number.isFinite(pilot.altitude)) return;
    const inBoundary = pointInPolygon(pilot.latitude, pilot.longitude, airport.boundingBox);
    if (inBoundary && pilot.altitude < airport.elevation + 200 && plan.departure === icao) {
      currentGround.add(pilot.callsign);
    } else if (!inBoundary && plan.arrival === icao
      && pilot.altitude > airport.elevation + 200
      && haversineKm(pilot.latitude, pilot.longitude, midpoint.lat, midpoint.lon) <= 50) {
      currentApproach.add(pilot.callsign);
    }
  });
  tracker.onGround.forEach((callsign) => {
    if (!currentGround.has(callsign) && connectedCallsigns.has(callsign)) tracker.departures.push(now);
  });
  tracker.onApproach.forEach((callsign) => {
    if (!currentApproach.has(callsign) && connectedCallsigns.has(callsign)) tracker.arrivals.push(now);
  });
  tracker.onGround = currentGround;
  tracker.onApproach = currentApproach;
}

function showAirport(icao) {
  state.airport = icao;
  if (!icao) {
    updateMetrics({ rollingDepartures: 0, hourlyDepartures: 0, rollingArrivals: 0, hourlyArrivals: 0 });
    drawChart(document.querySelector("#live-chart"), []);
    status.textContent = `Tracking all ${Object.keys(state.trackers).length} airports in the background. Choose one to view its rates.`;
    return;
  }
  const tracker = state.trackers[icao];
  const rates = calculateRates(tracker, Date.now());
  updateMetrics(rates);
  drawChart(document.querySelector("#live-chart"), tracker.samples);
  status.textContent = `Showing ${icao}; all ${Object.keys(state.trackers).length} airports continue tracking in the background.`;
}

async function poll() {
  try {
    const response = await fetch(VATSIM_DATA_URL);
    if (!response.ok) throw new Error(`VATSIM returned ${response.status}`);
    const data = await response.json();
    const now = Date.now();
    const pilots = data.pilots || [];
    const connectedCallsigns = new Set(pilots.map((pilot) => pilot.callsign));
    Object.entries(state.trackers).forEach(([icao, tracker]) => {
      processAirport(icao, pilots, connectedCallsigns, now);
      const rates = calculateRates(tracker, now);
      tracker.samples = [...tracker.samples, { time: now, ...rates }]
        .filter((sample) => now - sample.time <= SESSION_HISTORY_MS);
    });
    if (state.airport) {
      const tracker = state.trackers[state.airport];
      updateMetrics(calculateRates(tracker, now));
      drawChart(document.querySelector("#live-chart"), tracker.samples);
      status.textContent = `Showing ${state.airport}; all airports updated ${new Date(now).toLocaleTimeString()}.`;
    }
    persist();
  } catch (error) {
    status.textContent = `Unable to update live data: ${error.message}`;
  }
}

function startTracking() {
  poll();
  state.timer = setInterval(poll, POLL_INTERVAL_MS);
}

async function initialise() {
  try {
    const response = await fetch("boundingBoxes.json");
    if (!response.ok) throw new Error("Airport definitions could not be loaded.");
    state.airports = await response.json();
    state.trackers = Object.fromEntries(Object.entries(state.airports).map(([icao, airport]) => [
      icao,
      {
        airport,
        midpoint: airportMidpoint(airport.boundingBox),
        onGround: new Set(),
        onApproach: new Set(),
        departures: [],
        arrivals: [],
        samples: [],
      },
    ]));
    select.innerHTML = '<option value="">Choose an airport</option>'
      + Object.keys(state.airports).sort().map((icao) => `<option value="${icao}">${icao}</option>`).join("");
    select.disabled = false;
    if (!restore()) showAirport(null);
    startTracking();
  } catch (error) {
    status.textContent = error.message;
  }
}

select.addEventListener("change", () => {
  showAirport(select.value || null);
  persist();
});

window.addEventListener("pagehide", persist);

document.querySelector("#historic-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!window.HISTORIC_API_URL) {
    historicStatus.textContent = "Historic queries require a configured Cloudflare Worker URL.";
    return;
  }
  const button = event.currentTarget.querySelector("button");
  const formData = new FormData(event.currentTarget);
  const params = new URLSearchParams({
    icao: formData.get("icao").toUpperCase(),
    from: new Date(formData.get("from")).toISOString(),
    to: new Date(formData.get("to")).toISOString(),
  });
  button.disabled = true;
  historicStatus.textContent = "Fetching historic rates...";
  try {
    const response = await fetch(`${window.HISTORIC_API_URL}?${params}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Historic query failed.");
    drawChart(document.querySelector("#historic-chart"), result.samples);
    historicStatus.textContent = `${result.samples.length} historic movement timestamps returned.`;
  } catch (error) {
    historicStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

if (!window.HISTORIC_API_URL) {
  historicStatus.textContent = "Historic queries are disabled until a Worker URL is configured.";
}
drawChart(document.querySelector("#historic-chart"), []);
initialise();
