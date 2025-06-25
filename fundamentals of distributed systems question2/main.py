from flask import Flask, request, jsonify
import requests
import logging
import time
import threading
from typing import Dict, List

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Substation configurations
SUBSTATIONS = [
    {"name": "substation1", "url": "http://substation1:5000"},
    {"name": "substation2", "url": "http://substation2:5000"},
    {"name": "substation3", "url": "http://substation3:5000"}
]

# Store current loads for each substation
substation_loads = {}
load_lock = threading.Lock()

def get_substation_load(substation_url: str) -> float:
    """Get current load from a substation's metrics endpoint"""
    try:
        response = requests.get(f"{substation_url}/metrics", timeout=5)
        if response.status_code == 200:
            # Parse Prometheus metrics to extract current load
            metrics_text = response.text
            for line in metrics_text.split('\n'):
                if line.startswith('substation_current_load'):
                    # Extract the value from the metric line
                    value = line.split()[-1]
                    return float(value)
        return 0.0
    except Exception as e:
        logger.warning(f"Failed to get load from {substation_url}: {e}")
        return 100.0  # Assume high load if can't connect

def update_loads():
    """Periodically update loads from all substations"""
    while True:
        with load_lock:
            for substation in SUBSTATIONS:
                load = get_substation_load(substation["url"])
                substation_loads[substation["name"]] = load
                logger.info(f"{substation['name']} current load: {load:.1f}%")
        
        time.sleep(5)  # Update every 5 seconds

# Start background thread to monitor loads
threading.Thread(target=update_loads, daemon=True).start()

def find_least_loaded_substation() -> Dict:
    """Find the substation with the lowest current load"""
    with load_lock:
        if not substation_loads:
            # If no loads available yet, return first substation
            return SUBSTATIONS[0]
        
        # Find substation with minimum load
        min_load = float('inf')
        selected_substation = SUBSTATIONS[0]
        
        for substation in SUBSTATIONS:
            current_load = substation_loads.get(substation["name"], 100.0)
            if current_load < min_load:
                min_load = current_load
                selected_substation = substation
        
        logger.info(f"Selected {selected_substation['name']} with load {min_load:.1f}%")
        return selected_substation

@app.route('/route', methods=['POST'])
def route_request():
    """Route charging request to the least loaded substation"""
    try:
        # Get request data
        data = request.get_json() or {}
        
        # Find best substation
        selected_substation = find_least_loaded_substation()
        
        logger.info(f"Routing request to {selected_substation['name']}")
        
        # Forward request to selected substation
        response = requests.post(
            f"{selected_substation['url']}/charge",
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            substation_response = response.json()
            return jsonify({
                'status': 'success',
                'assigned_substation': selected_substation['name'],
                'substation_response': substation_response
            })
        else:
            logger.error(f"Substation {selected_substation['name']} returned error: {response.status_code}")
            return jsonify({
                'status': 'error',
                'message': f"Substation {selected_substation['name']} unavailable"
            }), 502
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error to substation: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Selected substation temporarily unavailable'
        }), 503
        
    except Exception as e:
        logger.error(f"Unexpected error in load balancer: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Load balancer internal error'
        }), 500

@app.route('/status')
def status():
    """Get current status of all substations"""
    with load_lock:
        return jsonify({
            'substations': substation_loads,
            'total_substations': len(SUBSTATIONS)
        })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'load_balancer'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)