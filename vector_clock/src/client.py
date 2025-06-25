# src/client.py

import requests
import time

def write(node, key, value):
    r = requests.post(f"http://localhost:{node}/put", json={"key": key, "value": value})
    print(f"[WRITE to {node}] {r.json()}")

def get(node, key):
    r = requests.get(f"http://localhost:{node}/get", params={"key": key})
    print(f"[GET from {node}] {r.json()}")

if __name__ == "__main__":
    # Simulate causal write: A then B depending on A
    write(5001, "x", "5")   # Node 1
    time.sleep(1)

    get(5002, "x")          # Node 2 reads x
    write(5002, "x", "10")  # Node 2 writes x again (depends on prior read)

    time.sleep(3)
    get(5003, "x")          # Node 3 should see causal ordering
