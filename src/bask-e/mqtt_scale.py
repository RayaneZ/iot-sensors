import time
import sys
import json
import gpiod
from hx711 import HX711
import paho.mqtt.client as mqtt

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

# Initialisation des objets
chip = None
hx = None
mqtt_client = mqtt.Client()

# --------------------- Fonctions Utilitaires ---------------------

def clean_and_exit():
    """Effectue un nettoyage propre et quitte le programme."""
    print("Nettoyage en cours...")
    try:
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


def calibrate(scale: HX711):
    # Remove any items from the scale
    input("Remove any items from scale. Press Enter when ready.")
    
    # Measure the offset (zero value)
    offset = scale.read_average()  # Get the average reading from HX711
    print(f"Value at zero (offset): {offset}")
    scale.set_offset(offset)  # Set the offset to zero
    
    # Ask user to place a known weight on the scale
    input("Please place an item of known weight on the scale. Press Enter when ready.")
    
    # Measure the weight with the object on the scale
    measured_weight = scale.read_average() - scale.get_offset()
    
    # Input the known weight in grams
    item_weight = float(input("Please enter the item's weight in grams:\n> "))
    
    # Calculate the scale adjustment factor
    scale_factor = measured_weight / item_weight
    
    # Set the scale based on the known weight
    scale.set_scale(scale_factor)
    print(f"Scale adjusted for grams: {scale_factor}")

def on_connect(client, userdata, flags, rc):
    """Callback exécuté lors de la connexion au broker MQTT."""
    if rc == 0:
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"Échec de connexion au broker MQTT, code : {rc}")

def on_message(client, userdata, msg):
    """Callback exécuté lors de la réception d'un message MQTT."""
    print(f"Message reçu sur {msg.topic} : {msg.payload}")

def initialize_mqtt():
    """Initialise et connecte le client MQTT."""
    try:
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Erreur de connexion au broker MQTT : {e}")
        clean_and_exit()

# --------------------- Gestion de la Balance ---------------------

def read_weight():
    """Lit le poids actuel de la balance."""
    try:
        weight = max(0, int(hx.get_weight(10)))  # Évite les valeurs négatives
        print(f"Poids mesuré : {weight} g")
        return weight
    except Exception as e:
        print(f"Erreur lors de la lecture du poids : {e}")
        return 0

def publish_weight(current_weight):
    """Publie le poids actuel via MQTT."""
    try:
        payload = json.dumps({
            'weight': current_weight,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        })
        mqtt_client.publish(MQTT_TOPIC_WEIGHT, payload)
        print(f"Publié sur MQTT : poids = {current_weight} g")
    except Exception as e:
        print(f"Erreur lors de la publication du poids : {e}")

# --------------------- Boucle Principale ---------------------

def main_loop():
    """Boucle principale pour lire et publier les poids."""
    try:
        while True:
            # Lire le poids actuel
            current_weight = read_weight()

            # Publier le poids
            publish_weight(current_weight)

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

    # Calibrer la balance
    calibrate()

    # Lancement de la boucle principale
    main_loop()
