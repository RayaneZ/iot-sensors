import time
import json
import threading
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import gpiod
from hx711 import HX711

# --------------------- Configuration ---------------------

# Configuration de la balance
REFERENCE_UNIT = 1
THRESHOLD = 10  # Seuil pour weight_mode en grammes

# Configuration MQTT
MQTT_BROKER = "mqtt.eclipseprojects.io"
MQTT_PORT = 1883
MQTT_TOPIC_WEIGHT = "scale/weight"
MQTT_TOPIC_WEIGHT_MODE = "scale/weight_mode"
MQTT_TOPIC_WEIGHT_CHANGE = "scale/weight_change"

# Variables globales
last_weight = {
    'value': 0,
    'timestamp': None
}
weight_mode = False
stop_thread = threading.Event()  # Event pour signaler l'arrêt du thread

# Initialisation des objets
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
chip = gpiod.chip("/dev/gpiochip0", gpiod.chip.OPEN_BY_PATH)
hx = HX711(dout=11, pd_sck=7, chip=chip)

# --------------------- Fonctions Utilitaires ---------------------

def tare_with_average(num_samples=10):
    """Effectue la tare avec une moyenne basée sur plusieurs lectures."""
    total = sum(hx.get_weight(5) for _ in range(num_samples))
    average = total / num_samples
    hx.set_offset(average)
    print(f"Tare réalisée avec une moyenne de {average:.2f} g.")

def initialize_hx711():
    """Initialise la balance HX711."""
    try:
        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(REFERENCE_UNIT)
        hx.reset()
        tare_with_average()
        print("Balance initialisée avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la balance : {e}")
        raise

def update_weight_mode():
    """Met à jour l'état du mode de détection de poids."""
    global weight_mode
    current_time = datetime.now()
    if last_weight['value'] > THRESHOLD and last_weight['timestamp']:
        elapsed = current_time - last_weight['timestamp']
        weight_mode = elapsed <= timedelta(minutes=1)
    else:
        weight_mode = False

    # Publier l'état du mode de poids
    try:
        msg_info = mqtt_client.publish(MQTT_TOPIC_WEIGHT_MODE, json.dumps({
            'weight_mode': weight_mode,
            'timestamp': current_time.isoformat()
        }))
        msg_info.wait_for_publish()
        print(f"Publié sur MQTT : weight_mode = {weight_mode}")
    except Exception as e:
        print(f"Erreur lors de la publication du mode de poids : {e}")

def publish_weight_change(current_weight):
    """Publie les changements de poids sur MQTT."""
    global last_weight
    delta = current_weight - last_weight['value']

    try:
        msg_info = mqtt_client.publish(MQTT_TOPIC_WEIGHT_CHANGE, json.dumps({
            'delta': delta,
            'current_weight': current_weight,
            'timestamp': datetime.now().isoformat()
        }))
        msg_info.wait_for_publish()
        print(f"Publié sur MQTT : changement de poids = {delta} g, poids actuel = {current_weight} g")
    except Exception as e:
        print(f"Erreur lors de la publication du changement de poids : {e}")

    last_weight['value'] = current_weight
    last_weight['timestamp'] = datetime.now()

def continuous_weight_read():
    """Lecture continue des poids et publication via MQTT."""
    while not stop_thread.is_set():
        try:
            # Lire le poids actuel
            current_weight = max(0, int(hx.get_weight(10)))  # Éviter les valeurs négatives
            print(f"Poids mesuré : {current_weight} g")

            # Publier le poids actuel
            msg_info = mqtt_client.publish(MQTT_TOPIC_WEIGHT, json.dumps({
                'weight': current_weight,
                'timestamp': datetime.now().isoformat()
            }))
            msg_info.wait_for_publish()
            print(f"Publié sur MQTT : poids = {current_weight} g")

            # Publier les changements de poids et mettre à jour le mode
            publish_weight_change(current_weight)
            update_weight_mode()

            # Réinitialiser la balance pour économiser l'énergie
            hx.power_down()
            hx.power_up()

            time.sleep(0.5)
        except Exception as e:
            print(f"Erreur lors de la lecture ou publication des données : {e}")
            time.sleep(1)  # Pause pour éviter les boucles excessives en cas d'erreur

# --------------------- Programme Principal ---------------------

if __name__ == '__main__':
    try:
        # Initialisation des composants
        print("Initialisation de la balance...")
        initialize_hx711()

        # Connexion au broker MQTT
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")

        # Démarrage du thread de lecture continue
        read_thread = threading.Thread(target=continuous_weight_read, daemon=True)
        read_thread.start()

        # Boucle principale pour garder le programme actif
        while True:
            time.sleep(1)  # Garde le thread principal actif

    except KeyboardInterrupt:
        print("Interruption par l'utilisateur. Fermeture du programme...")
        stop_thread.set()  # Signale au thread de s'arrêter
        read_thread.join()  # Attend la fin du thread
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Programme terminé proprement.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        stop_thread.set()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
