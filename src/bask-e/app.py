import requests
import json
import time
import sys
import paho.mqtt.client as mqtt

# ------------------ Configuration ------------------
THINGSBOARD_BASE_URL = "https://iot-5etoiles.bnf.sigl.epita.fr"
TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJwaWVycmUubWVpc3NAZXBpdGEuZnIiLCJ1c2VySWQiOiI5MjFjOWU1MC05OTA1LTExZWYtYWY1MC05MTEzNjViMDQyNWYiLCJzY29wZXMiOlsiVEVOQU5UX0FETUlOIl0sInNlc3Npb25JZCI6IjQxMTM4MWFhLTE5NWYtNDZjMC04YWUzLWVkMzI0ODE0MDliOSIsImV4cCI6MTc1NTk2MDA3NSwiaXNzIjoidGhpbmdzYm9hcmQuaW8iLCJpYXQiOjE3MzQ0ODUyMzksImZpcnN0TmFtZSI6IlBpZXJyZSIsImxhc3ROYW1lIjoiTWVpc3MiLCJlbmFibGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiNjg1MjM5NDAtOTkwNS0xMWVmLWFmNTAtOTExMzY1YjA0MjVmIiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.asv2tuEvU8MoUZODqDsu4p05kmNzHgqXA8awxGZoBFGEqDftjuonXCYdtvaY-vUexeeYqxlpTIh6J-KfxNY5Kg"
MQTT_BROKER = "mqtt.eclipseprojects.io"
MQTT_PORT = 1883

REFERENCIEL_UPDATE_RATE = 10 # secondes

# Table de correspondance entre labels YOLO et IDs produits
YOLO_LABELS_TO_PRODUCT_ID = {
    'banana': 1,
    'bottle': 3,
    'toothbrush': 4,
    'apple': 5
}

# URLs Thingsboard
ATTRIBUTE_URL = f"{THINGSBOARD_BASE_URL}/api/plugins/telemetry/ASSET/495a4310-a810-11ef-8ecc-15f62f1e4cc0/values/attributes"
TELEMETRY_URL = f"{THINGSBOARD_BASE_URL}/api/v1/muOVFVkq5YWhvpGoSmJq/telemetry"
PAYMENT_STATUS_URL = f"{THINGSBOARD_BASE_URL}/api/plugins/telemetry/DEVICE/5f680200-a2ca-11ef-8ecc-15f62f1e4cc0/attributes/SHARED_SCOPE"

last_data_scale = {"weight": 0, "difference": 0, "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S')}
last_data_obj = []

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
        if response.content:
            return response.json()
        else:
            log("Réponse vide reçue du serveur.", "WARNING")
            return None
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
            log(f"Produits chargés : {self.product_references}")
        else:
            log("Impossible de charger les produits de référence.", "ERROR")

    def get_product_id_from_yolo_label(self, yolo_label):
        """Récupère l'ID du produit correspondant au label YOLO."""
        log(f"Association de {yolo_label} avec ref produit id : {YOLO_LABELS_TO_PRODUCT_ID.get(yolo_label.lower())}")
        return YOLO_LABELS_TO_PRODUCT_ID.get(yolo_label.lower())

    def get_product_by_id(self, object_label):
        """Récupère un produit par ID."""
        log(f"HERRRRREEEEEE")
        log(f"Référentiel {self.product_references}")
        product_id = self.get_product_id_from_yolo_label(object_label)
        log(f"Product_id table : {product_id}")
        if product_id:
            log("Recherche de produit dans le ref produit") 
            res = None
            for p in self.product_references:
                log(f"Current product {p}")
                if p['id'] == product_id:
                    log(f"Product trouvé")
                    res = p
                    break
            print(f"Le résultat est {res}")
            return res
        else:
            log("Pas de produit correspondant au label")
            return None

    def update_cart(self):#, object_label, action):
        """Ajoute ou retire un produit dans le panier."""
        log(f"Mis à jour du panier dans thingsboard, cart : {self.product_list}")
        #product = self.get_product_by_id(object_label)
        #if product:
        #    if self.cart_error:
        #        self.cart_error = False
        #    if action == 'add':
        #        self.product_list.append(product)
        #        log(f"Produit ajouté : {product['name']}")
        #    elif action == 'remove' and product in self.product_list:
        #        self.product_list.remove(product)
        #        log(f"Produit retiré : {product['name']}")
        #    else:
        #        log(f"Action inconnue ou produit non trouvé : {object_label}", "WARNING")
        #else:
        #    self.cart_error = True
        self.calculate_total_price()
        self.send_telemetry()

    def calculate_total_price(self):
        """Calcule le prix total du panier."""
        self.total_price = sum(p['price'] for p in self.product_list)

    def send_telemetry(self):
        """Envoie les données du panier à Thingsboard."""
        log("Envoi des données à thingsboard")
            
        # Formatage de la liste des produits avec les bons types
        formatted_products = []
        for product in self.product_list:
            formatted_product = {
                "id": int(product['id']),
                "name": product['name'],
                "price": float(product['price']),
                "weight": int(product['weight']),
                "nutriScore": product['nutri-score'],
                "category": product['category'],
                "image": product['image'],
                "stock": int(product['stock'])
            }
            formatted_products.append(formatted_product)
            log(f"Produit formaté : {json.dumps(formatted_product, indent=2)}")
            
        payload = {
            "productList": formatted_products,
            "totalPrice": float(self.total_price),
            "cartError": bool(self.cart_error)
        }
        log(f"Payload complet : {json.dumps(payload, indent=2)}")

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
        self.client.subscribe("scale/weight")
        self.client.subscribe("camera/objects/detected")
        self.client.loop_start()

    # ------------ Callbacks ------------

    @staticmethod
    def on_connect(client, userdata, flags, rc, other):
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
            elif topic == "scale/weight":
                self.handle_weight_change(data)
            elif topic == "camera/objects/detected":
                self.handle_objects_detected(data)
        except json.JSONDecodeError as e:
            log(f"Erreur de décodage JSON : {e}", "ERROR")

    # ------------ Gestion des messages ------------

    def handle_nfc_message(self, data):
        if self.cart.total_price > 0:
            log(f"Paiement de {self.cart.total_price}€ effectué.")
            self.cart.product_list = []
            self.cart.total_price = 0
            self.cart.send_telemetry()
            self.cart.send_payment_status(True)
        else:
            self.cart.send_payment_status(False)

    last_timestamp = 0
    def handle_weight_change(self, data):
        global last_timestamp, REFERENCIEL_UPDATE_RATE
        # log("Changement de poids détecté :")
        # delta = data.get('delta', 0)
        # for product in self.cart.product_references:
        #     if abs(abs(delta) - product['weight']) <= 5:
        #         action = 'add' if delta > 0 else 'remove'
        # self.cart.update_cart()
        global last_data_scale
        last_data_scale = data
   
        current_timestamp = int(time.time())
        if current_timestamp - last_timestamp >= REFERENCIEL_UPDATE_RATE:
            self.cart.load_product_references()
            last_timestamp = current_timestamp
        log(f"Data : {data}")    

    def handle_objects_detected(self, objects):
        global last_data_obj, last_data_scale
        last_data_obj = objects  

        log(f"Last data scale : {last_data_scale}")
        
        total_weight, timestamp, weight_delta = last_data_scale["weight"], last_data_scale["timestamp"], last_data_scale["difference"]  
        
        self.cart.product_list = []
        supposed_total_weight = 0
        self.cart.cart_error = False
        for obj in objects:
            label, count, diff = obj["label"], obj["count"], obj["difference"]

            # Vérifier le cas d'un ajout d'objet :
            # if float(last_data_scale["difference"]) >= 0.0 and float(diff) >= 0.0:
                # Chercher le produit correspondant dans le panier
            product = self.cart.get_product_by_id(label)
            if product:
                # Si un produit est trouvé, l'ajouter au panier
                product["count"] = count
                supposed_total_weight += product["weight"] 

                self.cart.product_list.append(product)
                print(f"Added product: {product}")
            else:
                # Si le produit n'existe pas dans le catalogue, lever une erreur
                self.cart.cart_error = True
                print(f"Error: Product {label} not found in catalog.")
                break

            # Vérifier le cas d'un retrait d'objet :
            # elif float(last_data_scale["difference"]) < 0.0 and float(diff) < 0.0:
            #     product = self.cart.get_product_by_id(label)
            #     if product and product in self.cart.product_list:
            #         self.cart.product_list.remove(product)
            #         print(f"Removed product: {label}")
            #     else:
            #         print(f"Error: Product {label} not in cart.")

        log(f"Supposed total weight : {supposed_total_weight}, Total Weight : {total_weight}")
        acceptance_interval = 35
        if total_weight < supposed_total_weight - acceptance_interval or total_weight > supposed_total_weight + acceptance_interval : # Si y'a un problème de poids par rapport au poids qu'on a dans le ref produit
             log("Check du poids error")
             self.cart.cart_error = True
        self.cart.update_cart()
        log(f"cart : {self.cart.product_list}")

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
