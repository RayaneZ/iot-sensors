import time
import sys
import json
import gpiod
from hx711 import HX711
import paho.mqtt.client as mqtt
from threading import Event, Thread

# --------------------- Configuration ---------------------

# Configuration de la balance
REFERENCE_UNIT = 1
THRESHOLD = 10  # Seuil pour poids en grammes

# Configuration MQTT
MQTT_BROKER = "mqtt.eclipseprojects.io"
MQTT_PORT = 1883
MQTT_TOPIC_WEIGHT = "scale/weight"

# Variables globales
weight_mode = False
previous_weight = 0  # Dernier poids enregistré
stop_thread = Event()  # Signal pour arrêter les threads

# Initialisation des objets
chip = None
hx = None
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# --------------------- Fonctions Utilitaires ---------------------

def clean_and_exit():
    """Effectue un nettoyage propre et quitte le programme."""
    print("Nettoyage en cours...")
    try:
        stop_thread.set()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    except Exception as e:
        print(f"Erreur lors de la déconnexion MQTT : {e}")
    print("Programme arrêté proprement.")
    sys.exit()

def initialize_hx711():
    """Initialise le capteur HX711."""
    global chip, hx
    try:
        chip = gpiod.chip("/dev/gpiochip0", gpiod.chip.OPEN_BY_PATH)
        hx = HX711(dout=11, pd_sck=7, chip=chip)

        hx.set_reading_format("MSB", "MSB")
        hx.set_reference_unit(REFERENCE_UNIT)
        hx.reset()
        tare_with_average()
        print("Balance initialisée et tare effectuée.")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la balance : {e}")
        clean_and_exit()

def tare_with_average(num_samples=10):
    """Effectue la tare avec une moyenne basée sur plusieurs lectures."""
    try:
        total = sum(hx.get_weight(5) for _ in range(num_samples))
        average = total / num_samples
        hx.set_offset(average)
        print(f"Tare réalisée avec une moyenne de {average:.2f} g.")
    except Exception as e:
        print(f"Erreur lors de la tare : {e}")
        clean_and_exit()

def on_connect(client, userdata, flags, rc):
    """Callback exécuté lors de la connexion au broker MQTT."""
    if rc == 0:
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"Échec de connexion au broker MQTT, code : {rc}")

def initialize_mqtt():
    """Initialise et connecte le client MQTT."""
    try:
        mqtt_client.on_connect = on_connect
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Erreur de connexion au broker MQTT : {e}")
        clean_and_exit()

# --------------------- Gestion de la Balance ---------------------

def read_weight():
    """Lit le poids actuel de la balance."""
    try:
        weight = max(0, hx.get_weight(5))  # Évite les valeurs négatives
        print(f"Poids mesuré : {weight} g")
        return weight
    except Exception as e:
        print(f"Erreur lors de la lecture du poids : {e}")
        return 0

def publish_weight():
    """Boucle continue pour lire et publier les poids via MQTT."""
    global previous_weight
    while not stop_thread.is_set():
        current_weight = read_weight()

        if abs(current_weight - previous_weight) >= THRESHOLD:
            try:
                payload = json.dumps({
                    'weight': current_weight,
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
                })
                msg_info = mqtt_client.publish(MQTT_TOPIC_WEIGHT, payload)
                msg_info.wait_for_publish()
                print(f"Publié sur MQTT : poids = {current_weight} g")
                previous_weight = current_weight
            except Exception as e:
                print(f"Erreur lors de la publication du poids : {e}")

        time.sleep(0.5)  # Pause entre les lectures pour éviter les envois excessifs

# --------------------- Programme Principal ---------------------

if __name__ == '__main__':
    print("Initialisation du programme de balance...")

    # Initialisation des composants
    initialize_hx711()
    initialize_mqtt()

    # Lancer la publication dans un thread séparé
    try:
        mqtt_thread = Thread(target=publish_weight, daemon=True)
        mqtt_thread.start()

        while not stop_thread.is_set():
            time.sleep(1)  # Garde le programme principal actif
    except (KeyboardInterrupt, SystemExit):
        print("Interruption par l'utilisateur. Fermeture du programme...")
        clean_and_exit()
