from requests import post
from time import sleep
import threading
from flask import Flask, jsonify
import paho.mqtt.client as mqtt

app = Flask(__name__)
health_check_active = True

# Configuration MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_STATUS = "system/health/status"

# Variables globales MQTT
mqtt_client = mqtt.Client()

def collect_required_data():
    config = {
        "host": "iot-5etoiles.bnf.sigl.epita.fr",
        "token": "muOVFVkq5YWhvpGoSmJq",
        "username": "sysadmin@thingsboard.org", 
        "password": "sysadmin5etoilesiot"
    }
    return config

def get_auth_token(config):
    response = post(f"https://{config['host']}/api/auth/login",
                   json={
                       "username": config["username"],
                       "password": config["password"]
                   })
    return response.json().get("token")

def send_online_status(config, auth_token):
    """Envoie le statut "online" via HTTP et MQTT."""
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
            print(f"Publié sur MQTT : statut = online")
        
        sleep(10)

@app.route('/health/enable', methods=['POST'])
def enable_health_check():
    global health_check_active
    health_check_active = True
    
    # Publication MQTT
    mqtt_client.publish(MQTT_TOPIC_STATUS, "health_check_enabled")
    print("Publié sur MQTT : health_check_enabled")
    
    return jsonify({"status": "Health check enabled"})

@app.route('/health/disable', methods=['POST']) 
def disable_health_check():
    global health_check_active
    health_check_active = False

    # Publication MQTT
    mqtt_client.publish(MQTT_TOPIC_STATUS, "health_check_disabled")
    print("Publié sur MQTT : health_check_disabled")
    
    return jsonify({"status": "Health check disabled"})

@app.route('/health/status', methods=['GET'])
def get_health_status():
    return jsonify({
        "health_check_active": health_check_active
    })

if __name__ == '__main__':
    # Collecter la configuration
    config = collect_required_data()
    
    # Obtenir le token d'authentification
    auth_token = get_auth_token(config)
    
    # Connexion au broker MQTT
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Erreur de connexion au broker MQTT : {e}")
        exit(1)
    
    # Lancer le thread de statut en ligne
    status_thread = threading.Thread(target=send_online_status, args=(config, auth_token))
    status_thread.daemon = True
    status_thread.start()
    
    # Démarrer le serveur Flask
    app.run(host='0.0.0.0', port=5001)
