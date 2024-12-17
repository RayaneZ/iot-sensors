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

# mosquitto_sub -h localhost -t "nfc/card/read"
# mosquitto_sub -h localhost -t "nfc/payment_mode"

# MQTT Configuration
MQTT_BROKER = "mqtt.eclipseprojects.io"  # Remplacez par l'adresse IP du broker si nécessaire
MQTT_PORT = 1883
MQTT_TOPIC_READ = "nfc/card/read"
MQTT_TOPIC_PAYMENT_MODE = "nfc/payment_mode"
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Global variables to store last read data and payment mode
last_read = {
    'data': None,
    'timestamp': None
}
payment_mode = False  # Indique si le système est en mode paiement


def format_card_data(data):
    """Convert card data to JSON format"""
    try:
        return json.loads(data.decode('utf-8'))
    except:
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
    """Mise à jour du statut du mode paiement"""
    global payment_mode
    if last_read['data'] is not None and datetime.now() - last_read['timestamp'] <= timedelta(minutes=1):
        payment_mode = True
    else:
        payment_mode = False

    # Publier le statut du mode paiement sur MQTT
    mqtt_client.publish(MQTT_TOPIC_PAYMENT_MODE, json.dumps({
        'payment_mode': payment_mode,
        'timestamp': datetime.now().isoformat()
    }))
    print(f"Publié sur MQTT : payment_mode = {payment_mode}")


def continuous_read():
    """Lecture continue des cartes NFC et mise à jour des données"""
    global last_read
    while True:
        try:
            # Lecture de la carte NFC
            card_data = pn.read_mifare().get_data()
            formatted_data = format_card_data(card_data)
            last_read['data'] = formatted_data
            last_read['timestamp'] = datetime.now()

            # Publier les données NFC sur MQTT
            mqtt_client.publish(MQTT_TOPIC_READ, json.dumps({
                'data': formatted_data,
                'timestamp': last_read['timestamp'].isoformat()
            }))
            print(f"Publié sur MQTT : {formatted_data}")

            # Mettre à jour le mode paiement
            update_payment_mode()
        except Exception as e:
            print(f"Erreur de lecture NFC : {e}")
            time.sleep(0.1)  # Small delay to prevent CPU overuse
            continue

if __name__ == '__main__':
    # Connexion au broker MQTT
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Impossible de se connecter au broker MQTT : {e}")
        exit(1)

    # Démarrer la lecture continue dans un thread séparé
    read_thread = threading.Thread(target=continuous_read, daemon=True)
    read_thread.start()

