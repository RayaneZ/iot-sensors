import paho.mqtt.client as mqtt
import time

# Callback lorsque le client se connecte au broker
def on_connect(client, userdata, flags, rc):
    print("Connecté avec le code de résultat: " + str(rc))
    client.subscribe("test/topic")  # S'abonner à un topic

# Callback lorsque le client reçoit un message
def on_message(client, userdata, msg):
    print(f"Message reçu sur {msg.topic}: {msg.payload.decode()}")

# Création d'un client MQTT
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Assignation des callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connexion au broker MQTT (remplacez par l'adresse de votre broker)
client.connect("mqtt.eclipseprojects.io", 1883, 60)

# Boucle pour traiter les messages
client.loop_start()

# Publier un message sur le topic
client.publish("test/topic", "Hello MQTT!")

# Garder le script en cours d'exécution
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Déconnexion...")
    client.loop_stop()
    client.disconnect()
