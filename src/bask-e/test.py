import logging
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.DEBUG)

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.enable_logger()

mqttc.connect("mqtt.eclipseprojects.io", 1883, 60)
mqttc.loop_start()