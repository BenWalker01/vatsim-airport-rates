#!/usr/bin/env python3
"""
Simple CORS proxy server for VATSIM data
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VATSIM_API_URL = 'https://data.vatsim.net/v3/pilot-positions-structure.json'

@app.route('/api/pilots', methods=['GET'])
def get_pilots():
    """Fetch pilot data from VATSIM API"""
    try:
        response = requests.get(VATSIM_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Fetched {len(data.get('pilots', []))} pilots from VATSIM")
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch VATSIM data: {e}")
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/', methods=['GET'])
def index():
    """Index page"""
    return jsonify({
        'message': 'VATSIM Airport Rates API',
        'endpoints': {
            '/api/pilots': 'GET - Fetch VATSIM pilot data',
            '/api/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    print("Starting VATSIM Airport Rates API server...")
    print("Server running at http://127.0.0.1:5000")
    print("Access the app at http://127.0.0.1:8000")
    app.run(debug=True, port=5000)
