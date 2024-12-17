import requests
import json
import time
import sys
import paho.mqtt.client as mqtt

# ------------------ Configuration ------------------
THINGSBOARD_BASE_URL = "https://iot-5etoiles.bnf.sigl.epita.fr"
TOKEN = "muOVFVkq5YWhvpGoSmJq"
MQTT_BROKER = "mqtt.eclipseprojects.io"
MQTT_PORT = 1883

# Table de correspondance entre labels YOLO et IDs produits
YOLO_LABELS_TO_PRODUCT_ID = {
    'banana': '1',
    'orange': '18818888',
    'bottle': '3',
}

# URLs Thingsboard
ATTRIBUTE_URL = f"{THINGSBOARD_BASE_URL}/api/plugins/telemetry/ASSET/495a4310-a810-11ef-8ecc-15f62f1e4cc0/values/attributes"
TELEMETRY_URL = f"{THINGSBOARD_BASE_URL}/api/v1/muOVFVkq5YWhvpGoSmJq/telemetry"
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
        self.cart_error = False
        self.total_price = 0
        self.load_product_references()

    def load_product_references(self):
        """Charge les produits de référence depuis Thingsboard."""
        headers = {"Authorization": f"Bearer {self.token}"}
        data = send_request(ATTRIBUTE_URL, "GET", headers)
        if data:
            self.product_references = [item['value'] for item in data]
            log(f"Produits chargés")
        else:
            log("Impossible de charger les produits de référence.", "ERROR")

    def get_product_by_id(self, product_id):
        """Récupère un produit par ID."""
        return next((p for p in self.product_references if p['id'] == product_id), None)

    def get_product_id_from_yolo_label(self, yolo_label):
        """Récupère l'ID du produit correspondant au label YOLO."""
        return YOLO_LABELS_TO_PRODUCT_ID.get(yolo_label.lower())

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
            else:
                log(f"Action inconnue ou produit non trouvé : {product_id}", "WARNING")
            self.calculate_total_price()
            self.send_telemetry()

    def calculate_total_price(self):
        """Calcule le prix total du panier."""
        self.total_price = sum(p['price'] for p in self.product_list)

    def send_telemetry(self):
        """Envoie les données du panier à Thingsboard."""
        payload = {
            "productList": [p for p in self.product_list],
            "totalPrice": self.total_price,
            "cartError": self.cart_error
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
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.configure_client()

    def configure_client(self):
        """Configuration du client MQTT."""
        try:
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            log(f"Connecté au broker MQTT {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            log(f"Erreur de connexion MQTT : {e}", "ERROR")
            sys.exit(1)

        # Abonnements
        self.client.subscribe("nfc/card/read")
        self.client.subscribe("scale/weight_change")
        self.client.subscribe("camera/objects/detected")
        self.client.loop_start()

    # ------------ Callbacks ------------

    def on_connect(self, client, userdata, flags, rc):
        """Callback appelé lors de la connexion au broker."""
        log(f"Connecté au broker MQTT avec le code de résultat : {rc}")

    def on_message(self, client, userdata, message):
        """Callback appelé lors de la réception d'un message."""
        topic = message.topic
        payload = message.payload.decode()
        log(f"Message reçu sur le topic {topic}: {payload}")

        try:
            data = json.loads(payload)
            if topic == "nfc/card/read":
                self.handle_nfc_message(data)
            elif topic == "scale/weight_change":
                self.handle_weight_change(data)
            elif topic == "camera/objects/detected":
                self.handle_objects_detected(data)
        except json.JSONDecodeError as e:
            log(f"Erreur de décodage JSON : {e}", "ERROR")

    # ------------ Gestion des messages ------------

    def handle_nfc_message(self, data):
        if data.get('payment_mode') and self.cart.total_price > 0:
            log(f"Paiement de {self.cart.total_price}€ effectué.")
            self.cart.product_list = []
            self.cart.total_price = 0
            self.cart.send_telemetry()
            self.cart.send_payment_status(True)
        else:
            self.cart.send_payment_status(False)

    def handle_weight_change(self, data):
        delta = data.get('delta', 0)
        for product in self.cart.product_references:
            if abs(abs(delta) - product['weight']) <= 5:
                action = 'add' if delta > 0 else 'remove'
                self.cart.update_cart(product['id'], action)
                break

    def on_objects_detected(self, client, userdata, message): # FIXME
        data = self.parse_message(message)
        objects = data.get('detections', [])
        cart_error = False
        validated_objects = []

        log("Objets détectés :")
        for obj in objects:
            label = obj['label'].lower()
            score = obj['score']
            
            # Récupérer l'ID du produit via la table de correspondance
            product_id = self.cart.get_product_id_from_yolo_label(label)
            
            if product_id:
                # Récupérer les informations complètes du produit
                product = self.cart.get_product_by_id(product_id)
                if product:
                    obj['product_info'] = product
                    validated_objects.append(obj)
                    log(f"- {label} (Confiance: {score:.2f}) - Validé avec le produit: {product['name']}")
                else:
                    cart_error = True
                    log(f"- {label} (Confiance: {score:.2f}) - ID produit trouvé mais produit non trouvé", "WARNING")
            else:
                cart_error = True
                log(f"- {label} (Confiance: {score:.2f}) - Label non associé à un produit", "WARNING")

        # Mettre à jour le statut d'erreur du panier
        self.cart.cart_error = cart_error
        
        # Publier le résultat de la validation
        validation_result = {
            'detections': validated_objects,
            'cart_error': cart_error,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
        }
        self.client.publish('camera/objects/validated', json.dumps(validation_result, indent=4, ensure_ascii=False))

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
    try:
        cart = ShoppingCart(TOKEN)
        mqtt_handler = MQTTHandler(cart)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Interruption par l'utilisateur. Fermeture...")
        mqtt_handler.client.loop_stop()
        mqtt_handler.client.disconnect()
        log("Programme terminé proprement.")
