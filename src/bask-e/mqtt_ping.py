from requests import post
from time import sleep
import threading

# Configuration ThingsBoard
CONFIG = {
    "host": "iot-5etoiles.bnf.sigl.epita.fr",
    "token": "muOVFVkq5YWhvpGoSmJq",
    "username": "sysadmin@thingsboard.org", 
    "password": "sysadmin5etoilesiot"
}

# Variables globales
health_check_active = True

def collect_required_data():
    """
    Collecte les paramètres de configuration pour ThingsBoard.
    """
    return CONFIG

def get_auth_token(config):
    """
    Récupère le token d'authentification via une requête HTTP.
    """
    response = post(f"https://{config['host']}/api/auth/login",
                    json={ "username": config["username"], "password": config["password"] })
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print("Erreur : Impossible de récupérer le token d'authentification.")
        exit(1)

def send_online_status(config, auth_token):
    """
    Envoie périodiquement le statut 'online' via HTTP.
    """
    while True:
        if health_check_active:
            headers = {"Authorization": f"Bearer {auth_token}"}
            # Envoi HTTP
            response = post(f"https://{config['host']}/api/v1/{config['token']}/telemetry",
                            headers=headers,
                            json={"status": "online"})
            if response.status_code == 200:
                print("Statut envoyé : online via HTTP")
            else:
                print(f"Erreur lors de l'envoi du statut via HTTP : {response.status_code}")
        
        sleep(10)

if __name__ == '__main__':
    # Collecter la configuration
    config = collect_required_data()
    
    # Obtenir le token d'authentification
    auth_token = get_auth_token(config)
    
    # Lancer le thread de statut en ligne
    status_thread = threading.Thread(target=send_online_status, args=(config, auth_token))
    status_thread.daemon = True
    status_thread.start()
    
    # Le programme continue de tourner et envoie le statut toutes les 10 secondes.
    # Il n'y a plus de gestion des commandes utilisateur.
    print("Le statut 'online' est envoyé toutes les 10 secondes.")
    while True:
        sleep(1)  # Reste actif sans faire d'autres actions
