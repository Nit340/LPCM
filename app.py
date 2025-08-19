from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import threading
import time
import json
import os

app = Flask(__name__)

mqtt_client = None
connected = False
messages = []
latest_values = {}
mqtt_thread = None

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to broker with code {rc}")

def on_message(client, userdata, msg):
    global messages, latest_values
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
        latest_values.update(data)
    except json.JSONDecodeError:
        data = {"raw": payload}
    messages.append({
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "topic": msg.topic,
        "payload": payload
    })
    if len(messages) > 100:
        messages.pop(0)

def start_mqtt(broker, port, topic, username=None, password=None):
    global mqtt_client
    mqtt_client = mqtt.Client()
    if username and password:
        mqtt_client.username_pw_set(username, password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(broker, port, 60)
    mqtt_client.subscribe(topic)
    mqtt_client.loop_forever()

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect", methods=["POST"])
def connect():
    global connected, mqtt_thread
    if connected:
        return jsonify({"status": "already connected"})
    
    data = request.json
    broker = data.get("broker", "127.0.0.1")
    port = int(data.get("port", 1883))
    topic = data.get("topic", "#")
    mqtt_thread = threading.Thread(target=start_mqtt, args=(broker, port, topic, ), daemon=True)
    mqtt_thread.start()
    connected = True
    return jsonify({"status": "connected"})

@app.route("/disconnect", methods=["POST"])
def disconnect():
    global mqtt_client, connected
    if mqtt_client and connected:
        mqtt_client.disconnect()
        connected = False
        return jsonify({"status": "disconnected"})
    return jsonify({"status": "not connected"})

@app.route("/metrics")
def metrics():
    return jsonify(latest_values)

@app.route("/messages")
def get_messages():
    return jsonify(messages)

# Production-ready run
if __name__ == "__main__":
    # For Render or production, use gunicorn instead of debug server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
