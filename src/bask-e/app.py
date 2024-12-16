import requests
import json
import time
import sys
import paho.mqtt.client as mqtt
from time import sleep

class ShoppingCart:
    def __init__(self, token):
        self.token = token
        self.product_references = []
        self.product_list = []
        self.total_price = 0
        self.load_product_references()

    def load_product_references(self):
        """Récupère les produits référentiels depuis Thingsboard"""
        url = "https://iot-5etoiles.bnf.sigl.epita.fr/api/plugins/telemetry/ASSET/495a4310-a810-11ef-8ecc-15f62f1e4cc0/values/attributes"
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        try:
            # Effectuer la requête GET pour récupérer les données des produits
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Vérifie si la réponse est correcte (200 OK)
            # Extraire et stocker les produits référentiels
            data = response.json()
            self.product_references = [item['value'] for item in data]
            print("Produits récupérés depuis Thingsboard :")
            print(self.product_references)
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des produits depuis Thingsboard : {str(e)}")

    def get_product_by_id(self, product_id):
        """Récupère un produit à partir de son ID dans le référentiel"""
        for product in self.product_references:
            if product['id'] == product_id:
                return product
        return None

    def update_cart(self, product_id, action):
        """Met à jour le contenu du panier en ajoutant ou retirant un produit"""
        product = self.get_product_by_id(product_id)
        if product:
            if action == 'add':
                self.product_list.append(product)
            elif action == 'remove':
                self.product_list.remove(product)
        
        # Mise à jour du prix total et envoi des données à Thingsboard
        self.calculate_total_price()
        self.send_telemetry()

    def calculate_total_price(self):
        """Calcule le prix total en sommant les prix des produits du panier"""
        self.total_price = sum(product['price'] for product in self.product_list)

    def send_telemetry(self):
        """Envoie les données du panier à Thingsboard"""
        url = "https://iot-5etoiles.bnf.sigl.epita.fr/api/v1/5f680200-a2ca-11ef-8ecc-15f62f1e4cc0/telemetry"
        payload = {
            "productList": [{"id": p['id'], "name": p['name'], "price": p['price'], "weight": p['weight'], "category": p['category']} for p in self.product_list],
            "totalPrice": self.total_price
        }
        try:
            response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {self.token}"})
            response.raise_for_status()  # Vérifie si la requête est réussie
            print("Données envoyées à Thingsboard avec succès")
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de l'envoi des données à Thingsboard : {str(e)}")

if __name__ == '__main__':
    # Token pour accéder à Thingsboard
    token = "muOVFVkq5YWhvpGoSmJq"  # Token d'authentification Thingsboard
    
    # Configuration MQTT
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    mqtt_client = mqtt.Client()

    # Connexion au broker MQTT
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Impossible de se connecter au broker MQTT : {e}")
        sys.exit(1)

    # Initialisation du panier
    cart = ShoppingCart(token)

    def on_nfc_message(client, userdata, message):
        """Callback pour les messages NFC"""
        try:
            data = json.loads(message.payload)
            if data.get('payment_mode'):
                print("Carte de paiement détectée")
                # Déclencher le processus de paiement
                if cart.total_price > 0:
                    print(f"Paiement de {cart.total_price}€ initié")
                    # Réinitialiser le panier après paiement
                    cart.product_list = []
                    cart.total_price = 0
                    cart.send_telemetry()
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")

    def on_scale_message(client, userdata, message):
        """Callback pour les messages de la balance"""
        try:
            data = json.loads(message.payload)
            current_weight = data.get('weight', 0)
            print(f"Poids actuel: {current_weight}g")
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")

    def on_weight_change(client, userdata, message):
        """Callback pour les changements de poids"""
        try:
            data = json.loads(message.payload)
            delta = data.get('delta', 0)
            current_weight = data.get('current_weight', 0)
            
            # Recherche du produit correspondant au delta de poids
            if abs(delta) > 0:  # Si changement significatif
                for product in cart.product_references:
                    # Tolérance de 5g pour la détection
                    if abs(abs(delta) - product['weight']) <= 5:
                        if delta > 0:  # Ajout de produit
                            cart.update_cart(product['id'], 'add')
                            print(f"Produit ajouté: {product['name']}")
                        else:  # Retrait de produit
                            cart.update_cart(product['id'], 'remove')
                            print(f"Produit retiré: {product['name']}")
                        break
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")

    def on_payment_mode(client, userdata, message):
        """Callback pour le mode paiement"""
        try:
            data = json.loads(message.payload)
            payment_mode = data.get('payment_mode', False)
            if payment_mode:
                print("Mode paiement activé")
            else:
                print("Mode paiement désactivé") 
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")

    def on_weight_mode(client, userdata, message):
        """Callback pour le mode pesée"""
        try:
            data = json.loads(message.payload)
            weight_mode = data.get('weight_mode', False)
            if weight_mode:
                print("Mode pesée activé")
            else:
                print("Mode pesée désactivé")
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")

    # Souscription aux topics MQTT
    mqtt_client.subscribe("nfc/card/read")
    mqtt_client.subscribe("nfc/payment_mode") 
    mqtt_client.subscribe("scale/weight")
    mqtt_client.subscribe("scale/weight_change")
    mqtt_client.subscribe("scale/weight_mode")

    # Configuration des callbacks
    mqtt_client.message_callback_add("nfc/card/read", on_nfc_message)
    mqtt_client.message_callback_add("nfc/payment_mode", on_payment_mode)
    mqtt_client.message_callback_add("scale/weight", on_scale_message)
    mqtt_client.message_callback_add("scale/weight_change", on_weight_change)
    mqtt_client.message_callback_add("scale/weight_mode", on_weight_mode)

    # Démarrage de la boucle MQTT
    mqtt_client.loop_start()

    # Boucle principale
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt du programme...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
