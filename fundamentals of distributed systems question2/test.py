import requests
import threading
import time
import random
import json
from datetime import datetime

# Configuration
CHARGE_REQUEST_URL = "http://localhost:5001/request_charge"
NUM_VEHICLES = 50  # Number of EVs to simulate
REQUEST_DURATION = 120  # Run test for 2 minutes
RUSH_HOUR_INTENSITY = 3  # Requests per second during rush hour

# Statistics tracking
successful_requests = 0
failed_requests = 0
response_times = []
lock = threading.Lock()

def generate_ev_data():
    """Generate realistic EV charging request data"""
    vehicle_types = ["Tesla Model 3", "Nissan Leaf", "BMW i3", "Chevrolet Bolt", "Ford Mustang Mach-E"]
    
    return {
        "vehicle_id": f"EV_{random.randint(1000, 9999)}",
        "vehicle_type": random.choice(vehicle_types),
        "battery_level": random.randint(10, 40),  # Low battery levels
        "charging_power_needed": random.randint(25, 100),  # kW
        "estimated_charging_time": random.randint(30, 120),  # minutes
        "priority": random.choice(["normal", "high", "emergency"]),
        "timestamp": datetime.now().isoformat()
    }

def send_charging_request():
    """Send a single charging request and track statistics"""
    global successful_requests, failed_requests, response_times
    
    try:
        start_time = time.time()
        
        # Generate EV data
        ev_data = generate_ev_data()
        
        # Send request
        response = requests.post(
            CHARGE_REQUEST_URL, 
            json=ev_data, 
            timeout=10
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        with lock:
            response_times.append(response_time)
            if response.status_code == 200:
                successful_requests += 1
                print(f"✓ {ev_data['vehicle_id']} - Charging request successful ({response_time:.2f}s)")
            else:
                failed_requests += 1
                print(f"✗ {ev_data['vehicle_id']} - Request failed with status {response.status_code}")
                
    except requests.exceptions.RequestException as e:
        with lock:
            failed_requests += 1
        print(f"✗ Connection error: {e}")
    except Exception as e:
        with lock:
            failed_requests += 1
        print(f"✗ Unexpected error: {e}")

def simulate_rush_hour():
    """Simulate EV charging rush hour with varying intensity"""
    print("🚗 Starting EV Charging Rush Hour Simulation...")
    print(f"📊 Simulating {NUM_VEHICLES} EVs over {REQUEST_DURATION} seconds")
    print("-" * 60)
    
    start_time = time.time()
    
    # Create threads for concurrent requests
    threads = []
    
    for i in range(NUM_VEHICLES):
        # Vary the timing - more requests at the beginning (rush hour peak)
        if i < NUM_VEHICLES // 2:
            delay = random.uniform(0, REQUEST_DURATION // 3)  # First third - heavy load
        else:
            delay = random.uniform(REQUEST_DURATION // 3, REQUEST_DURATION)  # Spread out the rest
        
        # Create and schedule thread
        thread = threading.Timer(delay, send_charging_request)
        threads.append(thread)
        thread.start()
    
    # Wait for all requests to complete or timeout
    for thread in threads:
        thread.join()
    
    # Wait a bit more for any remaining responses
    time.sleep(5)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("-" * 60)
    print("📈 RUSH HOUR SIMULATION RESULTS:")
    print(f"⏱️  Total simulation time: {total_time:.1f} seconds")
    print(f"✅ Successful requests: {successful_requests}")
    print(f"❌ Failed requests: {failed_requests}")
    print(f"📊 Total requests: {successful_requests + failed_requests}")
    
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        print(f"⚡ Average response time: {avg_response_time:.2f} seconds")
        print(f"🐌 Slowest response: {max_response_time:.2f} seconds")
        print(f"🚀 Fastest response: {min_response_time:.2f} seconds")
    
    success_rate = (successful_requests / (successful_requests + failed_requests)) * 100 if (successful_requests + failed_requests) > 0 else 0
    print(f"🎯 Success rate: {success_rate:.1f}%")
    
    print("\n🔍 Check your Grafana dashboard to see the load balancing in action!")
    print("📈 Look for patterns in substation load distribution")

def test_system_health():
    """Test if the system is running before starting load test"""
    print("🔍 Checking system health...")
    
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Charge Request Service is healthy")
        else:
            print("⚠️  Charge Request Service may have issues")
    except:
        print("❌ Cannot connect to Charge Request Service")
        print("Make sure you run 'docker-compose up' first!")
        return False
    
    return True

if __name__ == "__main__":
    print("🔋 Smart Grid Load Balancer - Rush Hour Simulator")
    print("=" * 60)
    
    # Check system health first
    if not test_system_health():
        print("\n❌ System not ready. Please start the services first with:")
        print("   docker-compose up")
        exit(1)
    
    print("\n🚀 System is ready! Starting rush hour simulation in 3 seconds...")
    time.sleep(3)
    
    # Run the simulation
    simulate_rush_hour()