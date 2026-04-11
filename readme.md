# VATSIM Airport Rates

A web-based tool to measure the arrival and departure rates at airports on VATSIM in real-time.

## Local Development

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/vatsim-airport-rates.git
cd vatsim-airport-rates
```

2. Add the WASM target:
```bash
rustup target add wasm32-unknown-unknown
```

3. Install wasm-pack:
```bash
cargo install wasm-pack
```

### Building

Build the WASM module for development:
```bash
wasm-pack build --target web --dev
```

For optimized production builds:
```bash
wasm-pack build --release --target web
```

### Backend Setup

The app requires a backend server to proxy VATSIM API requests (to handle CORS restrictions).

Install dependencies:
```bash
pip install flask flask-cors requests
```

### Running Locally

1. **Start the backend server** (in one terminal):
```bash
python3 server.py
```

The API server will run at `http://127.0.0.1:5000`

2. **Start a web server** (in another terminal):

Using Python:
```bash
python3 -m http.server 8000
```

Using Node.js (http-server):
```bash
npx http-server
```

3. **Open the app** in your browser:
```
http://localhost:8000
```

## Deployment

The app is automatically deployed to GitHub Pages on every push to `main` via the GitHub Actions workflow. 

**Note:** GitHub Pages only hosts static files. For a live deployment with real VATSIM data fetching, you'll need to host the Python backend separately (e.g., on Render, Railway, or Heroku) and update the `API_URL` in `app.js`.

View the static version at:
https://yourusername.github.io/vatsim-airport-rates

## Features

- Track real-time pilot data from VATSIM
- Monitor arrival and departure rates at selected airports
- Supports any airport defined in [boundingBoxes.json](boundingBoxes.json)
- Export tracking data for analysis

## Usage

1. Enter an airport ICAO code (e.g., EGSS)
2. Click "Add" to start tracking
3. View real-time arrival and departure rates
4. Multiple airports can be tracked simultaneously
