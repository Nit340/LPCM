from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import threading
import time
import json

app = Flask(__name__)

mqtt_client = None
connected = False
messages = []
latest_values = {}

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to broker with code", rc)

def on_message(client, userdata, msg):
    global messages, latest_values
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
        latest_values = data
    except:
        data = {"raw": payload}

    messages.append({
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "topic": msg.topic,
        "payload": payload
    })
    if len(messages) > 100:
        messages.pop(0)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect", methods=["POST"])
def connect():
    global mqtt_client, connected
    if connected:
        return jsonify({"status": "already connected"})
    data = request.json
    broker = data.get("broker", "127.0.0.1")
    port = int(data.get("port", 1883))
    topic = data.get("topic", "#")

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    def run():
        mqtt_client.connect(broker, port, 60)
        mqtt_client.subscribe(topic)
        mqtt_client.loop_forever()

    threading.Thread(target=run, daemon=True).start()
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
