import requests
import json
import time
import sys
import paho.mqtt.client as mqtt

# ------------------ Configuration ------------------
THINGSBOARD_BASE_URL = "https://iot-5etoiles.bnf.sigl.epita.fr"
TOKEN = "muOVFVkq5YWhvpGoSmJq"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# URLs Thingsboard
ATTRIBUTE_URL = f"{THINGSBOARD_BASE_URL}/api/plugins/telemetry/ASSET/495a4310-a810-11ef-8ecc-15f62f1e4cc0/values/attributes"
TELEMETRY_URL = f"{THINGSBOARD_BASE_URL}/api/v1/5f680200-a2ca-11ef-8ecc-15f62f1e4cc0/telemetry"
PAYMENT_STATUS_URL = f"{THINGSBOARD_BASE_URL}/api/plugins/telemetry/DEVICE/5f680200-a2ca-11ef-8ecc-15f62f1e4cc0/attributes/SHARED_SCOPE"

# ------------------ Fonctions Utilitaires ------------------
def log(message, level="INFO"):
    """Affiche un message avec un niveau de priorité."""
    print(f"[{level}] {message}")

def send_request(url, method="GET", headers=None, payload=None):
    """Gère les requêtes HTTP avec gestion des exceptions."""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log(f"Erreur HTTP : {e}", "ERROR")
        return None

# ------------------ Classe ShoppingCart ------------------
class ShoppingCart:
    def __init__(self, token):
        self.token = token
        self.product_references = []
        self.product_list = []
        self.total_price = 0
        self.load_product_references()

    def load_product_references(self):
        """Charge les produits de référence depuis Thingsboard."""
        headers = {"Authorization": f"Bearer {self.token}"}
        data = send_request(ATTRIBUTE_URL, "GET", headers)
        if data:
            self.product_references = [item['value'] for item in data]
            log(f"Produits chargés : {self.product_references}")

    def get_product_by_id(self, product_id):
        """Récupère un produit par ID."""
        return next((p for p in self.product_references if p['id'] == product_id), None)

    def update_cart(self, product_id, action):
        """Ajoute ou retire un produit dans le panier."""
        product = self.get_product_by_id(product_id)
        if product:
            if action == 'add':
                self.product_list.append(product)
                log(f"Produit ajouté : {product['name']}")
            elif action == 'remove' and product in self.product_list:
                self.product_list.remove(product)
                log(f"Produit retiré : {product['name']}")
            self.calculate_total_price()
            self.send_telemetry()

    def calculate_total_price(self):
        """Calcule le prix total du panier."""
        self.total_price = sum(p['price'] for p in self.product_list)

    def send_telemetry(self):
        """Envoie les données du panier à Thingsboard."""
        payload = {
            "productList": [{
                "id": p['id'], "name": p['name'], "price": p['price'], "weight": p['weight'], "category": p['category']
            } for p in self.product_list],
            "totalPrice": self.total_price
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        send_request(TELEMETRY_URL, "POST", headers, payload)
        log("Données du panier envoyées.")

    def send_payment_status(self, is_paid):
        """Envoie l'état de paiement."""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"isPaid": is_paid}
        send_request(PAYMENT_STATUS_URL, "POST", headers, payload)
        log(f"Statut de paiement : {'Payé' if is_paid else 'Non payé'}")

# ------------------ Classe MQTTHandler ------------------
class MQTTHandler:
    def __init__(self, cart):
        self.cart = cart
        self.client = mqtt.Client()
        self.configure_client()

    def configure_client(self):
        """Configuration du client MQTT."""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            log(f"Connecté au broker MQTT {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            log(f"Erreur de connexion MQTT : {e}", "ERROR")
            sys.exit(1)

        # Abonnements
        self.client.message_callback_add("nfc/card/read", self.on_nfc_message)
        self.client.message_callback_add("scale/weight_change", self.on_weight_change)
        self.client.message_callback_add("camera/objects/detected", self.on_objects_detected)
        self.client.subscribe([
            ("nfc/card/read", 0),
            ("scale/weight_change", 0),
            ("camera/objects/detected", 0)
        ])

    # ------------ Callbacks ------------
    def on_nfc_message(self, client, userdata, message):
        data = self.parse_message(message)
        if data.get('payment_mode') and self.cart.total_price > 0:
            log(f"Paiement de {self.cart.total_price}€ effectué")
            self.cart.product_list = []
            self.cart.total_price = 0
            self.cart.send_telemetry()
            self.cart.send_payment_status(True)
        else:
            self.cart.send_payment_status(False)

    def on_weight_change(self, client, userdata, message):
        data = self.parse_message(message)
        delta = data.get('delta', 0)
        if abs(delta) > 0:
            for product in self.cart.product_references:
                if abs(abs(delta) - product['weight']) <= 5:
                    action = 'add' if delta > 0 else 'remove'
                    self.cart.update_cart(product['id'], action)
                    break

    def on_objects_detected(self, client, userdata, message):
        objects = self.parse_message(message)
        log("Objets détectés :")
        for obj in objects:
            log(f"- {obj['label']} (Confiance: {obj['score']})")

    # ------------ Utilitaires ------------
    @staticmethod
    def parse_message(message):
        try:
            return json.loads(message.payload)
        except json.JSONDecodeError as e:
            log(f"Erreur de décodage JSON : {e}", "ERROR")
            return {}

    def start(self):
        """Démarre la boucle MQTT."""
        self.client.loop_start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log("Arrêt du programme.")
            self.client.loop_stop()
            self.client.disconnect()

# ------------------ Main ------------------
if __name__ == "__main__":
    cart = ShoppingCart(TOKEN)
    mqtt_handler = MQTTHandler(cart)
    mqtt_handler.start()
