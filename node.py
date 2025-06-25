# src/node.py

from flask import Flask, request, jsonify
import threading
import time
import os
import requests
import json

app = Flask(__name__)

NODE_ID = os.getenv("NODE_ID")
PEERS = os.getenv("PEERS").split(",")
ALL_NODES = PEERS + [NODE_ID]

vector_clock = {node: 0 for node in ALL_NODES}
store = {}
buffer = []

lock = threading.Lock()


def increment_clock():
    vector_clock[NODE_ID] += 1


def update_clock(received_clock):
    for node, time in received_clock.items():
        vector_clock[node] = max(vector_clock[node], time)


def is_causally_ready(received_clock, sender_id):
    for node in vector_clock:
        if node == sender_id:
            if received_clock[node] != vector_clock[node] + 1:
                return False
        else:
            if received_clock[node] > vector_clock[node]:
                return False
    return True


@app.route("/put", methods=["POST"])
def put():
    data = request.json
    key, value = data["key"], data["value"]

    with lock:
        increment_clock()
        store[key] = (value, dict(vector_clock))

    replicate(key, value, dict(vector_clock))
    return jsonify({"status": "write stored and replicated"})


@app.route("/replicate", methods=["POST"])
def replicate_write():
    data = request.json
    key, value, received_clock, sender = data["key"], data["value"], data["clock"], data["sender"]

    with lock:
        if is_causally_ready(received_clock, sender):
            update_clock(received_clock)
            store[key] = (value, received_clock)
        else:
            buffer.append(data)

    return jsonify({"status": "replication attempted"})


@app.route("/get", methods=["GET"])
def get():
    key = request.args.get("key")
    if key in store:
        value, clock = store[key]
        return jsonify({"key": key, "value": value, "clock": clock})
    return jsonify({"error": "key not found"}), 404


def replicate(key, value, clock):
    for peer in PEERS:
        try:
            requests.post(f"http://{peer}:5000/replicate", json={
                "key": key,
                "value": value,
                "clock": clock,
                "sender": NODE_ID
            }, timeout=1)
        except requests.exceptions.RequestException:
            pass


def buffer_processor():
    while True:
        with lock:
            for msg in buffer[:]:
                if is_causally_ready(msg["clock"], msg["sender"]):
                    update_clock(msg["clock"])
                    store[msg["key"]] = (msg["value"], msg["clock"])
                    buffer.remove(msg)
        time.sleep(1)


if __name__ == "__main__":
    threading.Thread(target=buffer_processor, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
