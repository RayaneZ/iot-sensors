import paho.mqtt.client as mqtt

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    # Subscribe to all topics (wildcard '#')
    client.subscribe("#")  # Subscribe to all topics

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic} | Message: {str(msg.payload.decode('utf-8'))}")

# Create an MQTT client instance
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Assign callback functions
mqttc.on_connect = on_connect
mqttc.on_message = on_message

# Connect to the MQTT broker
mqttc.connect("mqtt.eclipseprojects.io", 1883, 60)

# Start the MQTT client loop to handle network traffic and dispatch callbacks
mqttc.loop_forever()
