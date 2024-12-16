from requests import post
from time import sleep
import threading
import paho.mqtt.client as mqtt

# Configuration MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_STATUS = "system/health/status"

# Variables globales
health_check_active = True
mqtt_client = mqtt.Client()

def collect_required_data():
    """
    Collecte les paramètres de configuration pour ThingsBoard.
    """
    config = {
        "host": "iot-5etoiles.bnf.sigl.epita.fr",
        "token": "muOVFVkq5YWhvpGoSmJq",
        "username": "sysadmin@thingsboard.org", 
        "password": "sysadmin5etoilesiot"
    }
    return config

def get_auth_token(config):
    """
    Récupère le token d'authentification via une requête HTTP.
    """
    response = post(f"https://{config['host']}/api/auth/login",
                    json={
                        "username": config["username"],
                        "password": config["password"]
                    })
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print("Erreur : Impossible de récupérer le token d'authentification.")
        exit(1)

def send_online_status(config, auth_token):
    """
    Envoie périodiquement le statut 'online' via HTTP et MQTT.
    """
    global health_check_active
    while True:
        if health_check_active:
            headers = {"Authorization": f"Bearer {auth_token}"}
            # Envoi HTTP
            post(f"https://{config['host']}/api/v1/{config['token']}/telemetry",
                 headers=headers,
                 json={"status": "online"})
            
            # Publication MQTT
            mqtt_client.publish(MQTT_TOPIC_STATUS, "online")
            print("Statut envoyé : online")
        
        sleep(10)

def enable_health_check():
    """
    Active le health check.
    """
    global health_check_active
    health_check_active = True
    mqtt_client.publish(MQTT_TOPIC_STATUS, "health_check_enabled")
    print("Health check activé et publié sur MQTT.")

def disable_health_check():
    """
    Désactive le health check.
    """
    global health_check_active
    health_check_active = False
    mqtt_client.publish(MQTT_TOPIC_STATUS, "health_check_disabled")
    print("Health check désactivé et publié sur MQTT.")

def mqtt_setup():
    """
    Configure la connexion MQTT.
    """
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Erreur de connexion au broker MQTT : {e}")
        exit(1)

def user_input_handler():
    """
    Gère les commandes utilisateur depuis la console pour activer/désactiver le health check.
    """
    global health_check_active
    print("\nCommandes disponibles :")
    print("  1. 'enable'  - Activer le health check")
    print("  2. 'disable' - Désactiver le health check")
    print("  3. 'quit'    - Quitter le programme")

    while True:
        user_input = input("\nEntrez une commande : ").strip().lower()
        if user_input == "enable":
            enable_health_check()
        elif user_input == "disable":
            disable_health_check()
        elif user_input == "quit":
            print("Arrêt du programme...")
            break
        else:
            print("Commande inconnue. Veuillez utiliser 'enable', 'disable' ou 'quit'.")

if __name__ == '__main__':
    # Collecter la configuration
    config = collect_required_data()
    
    # Obtenir le token d'authentification
    auth_token = get_auth_token(config)
    
    # Connexion au broker MQTT
    mqtt_setup()
    
    # Lancer le thread de statut en ligne
    status_thread = threading.Thread(target=send_online_status, args=(config, auth_token))
    status_thread.daemon = True
    status_thread.start()
    
    # Gérer les commandes utilisateur
    user_input_handler()
