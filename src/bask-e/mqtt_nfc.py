from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *
from datetime import datetime, timedelta
import json
import threading
import time
import paho.mqtt.client as mqtt

# Initialize NFC reader
pn = Pn532_i2c()
pn.SAMconfigure()

# MQTT Configuration
MQTT_BROKER = "mqtt.eclipseprojects.io"
MQTT_PORT = 1883
MQTT_TOPIC_READ = "nfc/card/read"
MQTT_TOPIC_PAYMENT_MODE = "nfc/payment_mode"

# Global variables
last_read = {
    'data': None,
    'timestamp': None
}
payment_mode = False
stop_thread = threading.Event()  # Event to signal thread termination

# MQTT client setup
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def format_card_data(data):
    """Convert card data to JSON format"""
    try:
        return json.loads(data.decode('utf-8'))
    except Exception:
        return {
            "raw_hex": data.hex(),
            "blocks": [
                {
                    "block": i,
                    "data": data[i:i+4].hex()
                } for i in range(0, len(data), 4)
            ]
        }

def update_payment_mode():
    """Update payment mode status"""
    global payment_mode
    if last_read['data'] and datetime.now() - last_read['timestamp'] <= timedelta(minutes=1):
        payment_mode = True
    else:
        payment_mode = False

    # Publish payment mode status to MQTT
    try:
        msg_info = mqtt_client.publish(MQTT_TOPIC_PAYMENT_MODE, json.dumps({
            'payment_mode': payment_mode,
            'timestamp': datetime.now().isoformat()
        }))
        msg_info.wait_for_publish()
        print(f"Publié sur MQTT : payment_mode = {payment_mode}")
    except Exception as e:
        print(f"Erreur lors de la publication du mode paiement : {e}")

def continuous_read():
    """Continuous NFC card reading"""
    global last_read
    while not stop_thread.is_set():
        try:
            # Read NFC card
            card_data = pn.read_mifare().get_data()
            formatted_data = format_card_data(card_data)
            last_read['data'] = formatted_data
            last_read['timestamp'] = datetime.now()

            # Publish NFC data to MQTT
            msg_info = mqtt_client.publish(MQTT_TOPIC_READ, json.dumps({
                'data': formatted_data,
                'timestamp': last_read['timestamp'].isoformat()
            }))
            msg_info.wait_for_publish()
            print(f"Publié sur MQTT : {formatted_data}")

            # Update payment mode
            update_payment_mode()
        except Exception as e:
            print(f"Erreur de lecture NFC : {e}")
            time.sleep(0.5)  # Small delay to prevent excessive retries

if __name__ == '__main__':
    try:
        # Connect to MQTT broker
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")

        # Start NFC reading thread
        read_thread = threading.Thread(target=continuous_read, daemon=True)
        read_thread.start()

        # Main loop to keep the script running
        while True:
            time.sleep(1)  # Keep the main thread alive

    except KeyboardInterrupt:
        print("Interruption par l'utilisateur. Fermeture du programme...")
        stop_thread.set()  # Signal the reading thread to stop
        read_thread.join()  # Wait for the thread to finish
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Programme terminé proprement.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
