const API_URL = 'http://127.0.0.1:5000/api/pilots';

// Wait for WASM to be initialized
async function waitForWasm() {
    let attempts = 0;
    while (!window.__WASM__ && attempts < 50) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
    }
    if (!window.__WASM__) {
        throw new Error('WASM failed to initialize');
    }
    return window.__WASM__;
}

// Store active airport tracking
const trackedAirports = new Map();

// DOM Elements
const airportInput = document.getElementById('airport-input');
const addBtn = document.getElementById('add-airport-btn');
const airportsList = document.getElementById('airports-list');
const template = document.getElementById('airport-card-template');

// Fetch VATSIM data from local backend
async function fetchVATSIMData() {
    try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (err) {
        console.error('Failed to fetch VATSIM data:', err);
        return null;
    }
}

// Add an airport to tracking
async function addAirport(icao) {
    icao = icao.toUpperCase().trim();
    
    if (!icao || icao.length !== 4) {
        showError('Please enter a valid 4-letter ICAO code');
        return;
    }
    
    if (trackedAirports.has(icao)) {
        showError(`${icao} is already being tracked`);
        return;
    }
    
    try {
        const wasm = await waitForWasm();
        
        // Create airport tracker (this would use WASM if implemented)
        trackedAirports.set(icao, {
            icao,
            startTime: new Date(),
            arrivals: [],
            departures: []
        });
        
        // Create and add card to DOM
        const card = template.content.cloneNode(true);
        const cardElement = card.querySelector('.airport-card');
        cardElement.id = `airport-${icao}`;
        
        card.querySelector('.airport-icao').textContent = icao;
        card.querySelector('.remove-btn').addEventListener('click', () => removeAirport(icao));
        
        airportsList.innerHTML = ''; // Clear empty state
        airportsList.appendChild(card);
        
        airportInput.value = '';
        showSuccess(`Added ${icao} to tracking`);
        
        // Start polling for data
        pollAirportData(icao);
    } catch (err) {
        showError(`Failed to add airport: ${err.message}`);
    }
}

// Remove an airport from tracking
function removeAirport(icao) {
    trackedAirports.delete(icao);
    const card = document.getElementById(`airport-${icao}`);
    if (card) {
        card.parentElement.removeChild(card);
    }
    
    if (trackedAirports.size === 0) {
        airportsList.innerHTML = '<p class="empty-state">No airports being tracked. Add one to get started.</p>';
    }
    
    showSuccess(`Removed ${icao} from tracking`);
}

// Poll and update airport data
async function pollAirportData(icao) {
    while (trackedAirports.has(icao)) {
        try {
            const data = await fetchVATSIMData();
            if (data) {
                updateAirportStats(icao, data);
            }
        } catch (err) {
            console.error(`Error polling data for ${icao}:`, err);
        }
        
        // Poll every 30 seconds
        await new Promise(resolve => setTimeout(resolve, 30000));
    }
}

// Update airport stats in DOM
function updateAirportStats(icao, vatsimData) {
    const cardElement = document.getElementById(`airport-${icao}`);
    if (!cardElement) return;
    
    // Parse VATSIM data to get relevant pilots
    // This is a placeholder - actual implementation would use boundary checking with WASM
    const stats = calculateStats(icao, vatsimData);
    
    cardElement.querySelector('.dep-rate').textContent = stats.departures.toString();
    cardElement.querySelector('.arr-rate').textContent = stats.arrivals.toString();
    cardElement.querySelector('.on-ground').textContent = stats.onGround.toString();
    cardElement.querySelector('.on-approach').textContent = stats.onApproach.toString();
}

// Calculate stats for an airport
function calculateStats(icao, vatsimData) {
    // This is a placeholder implementation
    // In a real implementation, this would use WASM boundary checking
    return {
        departures: Math.floor(Math.random() * 5),
        arrivals: Math.floor(Math.random() * 5),
        onGround: Math.floor(Math.random() * 10),
        onApproach: Math.floor(Math.random() * 3)
    };
}

// Show error message
function showError(message) {
    const div = document.createElement('div');
    div.className = 'error';
    div.textContent = message;
    document.body.insertBefore(div, document.body.firstChild);
    setTimeout(() => div.remove(), 4000);
}

// Show success message
function showSuccess(message) {
    const div = document.createElement('div');
    div.className = 'success';
    div.textContent = message;
    document.body.insertBefore(div, document.body.firstChild);
    setTimeout(() => div.remove(), 3000);
}

// Event listeners
addBtn.addEventListener('click', () => addAirport(airportInput.value));
airportInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        addAirport(airportInput.value);
    }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await waitForWasm();
        console.log('WASM initialized successfully');
    } catch (err) {
        console.error('Failed to initialize app:', err);
        showError('Failed to initialize app. Check console for details.');
    }
});
