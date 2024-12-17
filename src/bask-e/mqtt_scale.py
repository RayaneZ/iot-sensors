import time
import sys
import json
import gpiod
from hx711 import HX711
import paho.mqtt.client as mqtt

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
weight_mode = False
previous_weight = 0  # Dernier poids enregistré

# Initialisation des objets
chip = None
hx = None
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# --------------------- Fonctions Utilitaires ---------------------

def clean_and_exit():
    """Effectue un nettoyage propre et quitte le programme."""
    print("Nettoyage en cours...")
    mqtt_client.disconnect()
    print("Programme arrêté proprement.")
    sys.exit()

def initialize_hx711():
    """Initialise le capteur HX711."""
    global chip, hx
    chip = gpiod.chip("/dev/gpiochip0", gpiod.chip.OPEN_BY_PATH)
    hx = HX711(dout=11, pd_sck=7, chip=chip)

    hx.set_reading_format("MSB", "MSB")
    hx.set_reference_unit(REFERENCE_UNIT)
    hx.reset()
    tare_with_average()
    print("Balance initialisée et tare effectuée.")

def tare_with_average(num_samples=10):
    """Effectue la tare avec une moyenne basée sur plusieurs lectures."""
    total = sum(hx.get_weight(5) for _ in range(num_samples))
    average = total / num_samples
    hx.set_offset(average)
    print(f"Tare réalisée avec une moyenne de {average:.2f} g.")

def on_connect(client, userdata, flags, rc):
    print("Connecté avec le code de résultat " + str(rc))
    client.subscribe("$SYS/#")  # S'abonne à tous les sujets système

def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))

def initialize_mqtt():
    """Connecte le client MQTT au broker."""
    try:
        mqtt_client.on_connect = on_connect  # Ajout du callback on_connect
        mqtt_client.on_message = on_message    # Ajout du callback on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Erreur de connexion MQTT : {e}")
        clean_and_exit()

# --------------------- Gestion de la Balance ---------------------

def read_weight():
    """Lit le poids actuel de la balance."""
    weight = max(0, int(hx.get_weight(10)))  # Évite les valeurs négatives
    print(f"Poids mesuré : {weight} g")
    return weight

def update_weight_mode(current_weight):
    """Met à jour et publie le mode de détection de poids."""
    global weight_mode
    new_weight_mode = current_weight > THRESHOLD

    if new_weight_mode != weight_mode:
        weight_mode = new_weight_mode
        payload = json.dumps({
            'weight_mode': weight_mode,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        })
        mqtt_client.publish(MQTT_TOPIC_WEIGHT_MODE, payload)
        print(f"Publié sur MQTT : weight_mode = {weight_mode}")

def check_weight_change(current_weight):
    """Calcule et publie les changements de poids."""
    global previous_weight
    delta = current_weight - previous_weight

    payload = json.dumps({
        'delta': delta,
        'current_weight': current_weight,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    })
    mqtt_client.publish(MQTT_TOPIC_WEIGHT_CHANGE, payload)
    print(f"Publié sur MQTT : delta = {delta}, poids = {current_weight} g")

    previous_weight = current_weight

def publish_weight(current_weight):
    """Publie le poids actuel via MQTT."""
    payload = json.dumps({
        'weight': current_weight,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    })
    mqtt_client.publish(MQTT_TOPIC_WEIGHT, payload)
    print(f"Publié sur MQTT : poids = {current_weight} g")

# --------------------- Boucle Principale ---------------------

def main_loop():
    """Boucle principale pour lire et publier les poids."""
    try:
        while True:
            # Lire le poids actuel
            current_weight = read_weight()

            # Publier le poids et gérer les changements
            publish_weight(current_weight)
            update_weight_mode(current_weight)
            check_weight_change(current_weight)

            # Réinitialiser la balance pour économiser l'énergie
            hx.power_down()
            hx.power_up()
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        clean_and_exit()

# --------------------- Programme Principal ---------------------

if __name__ == '__main__':
    print("Initialisation du programme de balance...")

    # Initialisation des composants
    initialize_hx711()
    initialize_mqtt()

    # Lancement de la boucle principale
    main_loop()
