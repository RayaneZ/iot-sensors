import time
import sys
import json
import gpiod
from hx711 import HX711
import paho.mqtt.client as mqtt

# {
#    "delta": 15,
#    "current_weight": 120,
#    "timestamp": "2024-12-16T12:34:56"
#}


# Configuration de la balance
referenceUnit = 1
THRESHOLD = 10  # Seuil en grammes pour activer weight_mode

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_WEIGHT = "scale/weight"
MQTT_TOPIC_WEIGHT_MODE = "scale/weight_mode"
MQTT_TOPIC_WEIGHT_CHANGE = "scale/weight_change"

# Variables globales
chip = None
weight_mode = False
previous_weight = 0  # Dernier poids mesuré

# Initialisation MQTT
mqtt_client = mqtt.Client()

def cleanAndExit():
    """Nettoyage et sortie propre du programme."""
    print("Cleaning...")
    chip.close()
    mqtt_client.disconnect()
    print("Bye!")
    sys.exit()

# Initialisation du GPIO et de la balance
chip = gpiod.chip("/dev/gpiochip0", gpiod.chip.OPEN_BY_PATH)
hx = HX711(dout=11, pd_sck=7, chip=chip)

hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(referenceUnit)
hx.reset()

def tare_with_average(num_samples=10):
    """Effectue la tare en prenant la moyenne de plusieurs lectures."""
    total = 0
    for _ in range(num_samples):
        total += hx.get_weight(5)
        time.sleep(0.1)  # Petite pause entre les lectures
    average = total / num_samples
    hx.set_offset(average)  # Définir l'offset basé sur la moyenne
    print(f"Tare effectuée avec une moyenne de {average} g.")

print("Tare done! Add weight now...")
hx.tare()  # Remplacer par la nouvelle fonction
tare_with_average()  # Appeler la fonction de tare avec moyenne

def update_weight_mode(weight):
    """Mise à jour du mode de détection de poids."""
    global weight_mode
    new_weight_mode = weight > THRESHOLD
    if new_weight_mode != weight_mode:
        weight_mode = new_weight_mode
        mqtt_client.publish(MQTT_TOPIC_WEIGHT_MODE, json.dumps({
            'weight_mode': weight_mode,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        }))
        print(f"Publié sur MQTT : weight_mode = {weight_mode}")

def check_weight_change(current_weight):
    """Vérifie si le poids a changé, calcule le delta et publie les résultats."""
    global previous_weight

    delta = current_weight - previous_weight

    # Publier les changements de poids
    mqtt_client.publish(MQTT_TOPIC_WEIGHT_CHANGE, json.dumps({
        'delta': delta,
        'current_weight': current_weight,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    }))
    print(f"Publié sur MQTT : poids actuel = {current_weight}, delta = {delta}")

    # Mettre à jour le poids précédent
    previous_weight = current_weight

# Connexion au broker MQTT
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"Impossible de se connecter au broker MQTT : {e}")
    cleanAndExit()

# Boucle principale
try:
    while True:
        # Lire le poids actuel
        current_weight = max(0, int(hx.get_weight(10)))  # Convertir en entier et éviter les valeurs négatives
        print(f"Poids mesuré : {current_weight} g")

        # Publier le poids sur MQTT
        mqtt_client.publish(MQTT_TOPIC_WEIGHT, json.dumps({
            'weight': current_weight,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        }))
        print(f"Publié sur MQTT : poids = {current_weight} g")

        # Mettre à jour le mode de détection de poids
        update_weight_mode(current_weight)

        # Vérifier et publier les changements de poids
        check_weight_change(current_weight)

        # Réinitialiser la balance
        hx.power_down()
        hx.power_up()
        time.sleep(0.5)

except (KeyboardInterrupt, SystemExit):
    cleanAndExit()
