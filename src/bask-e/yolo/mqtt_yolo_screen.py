import cv2
import numpy as np
import json
from elements.yolo import OBJ_DETECTION
import paho.mqtt.client as mqtt
from collections import Counter

# ---------------- Configuration ----------------

# Classes et couleurs d'objets
OBJECT_CLASSES = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
                  'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
                  'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
                  'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
                  'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                  'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
                  'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
                  'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
                  'hair drier', 'toothbrush']

OBJECT_COLORS = np.random.randint(0, 255, size=(len(OBJECT_CLASSES), 3), dtype="uint8")

# YOLO Object Detector
OBJECT_DETECTOR = OBJ_DETECTION('/opt/bask-e/yolo/weights/yolov5s.pt', OBJECT_CLASSES)

# MQTT Configuration
MQTT_BROKER = "mqtt.eclipseprojects.io"  # Nouveau broker MQTT
MQTT_PORT = 1883
MQTT_TOPIC_READ = "camera/objects/detected"
MQTT_TOPIC_WEIGHT = "scale/weight"

# ---------------- Initialisation ----------------

def initialize_mqtt():
    """Initialise et connecte le client MQTT."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Erreur de connexion MQTT : {e}")
        exit(1)
    return client

def gstreamer_pipeline(capture_width=1920, capture_height=1080, display_width=960,
                       display_height=540, framerate=10, flip_method=0):
    """Retourne la pipeline GStreamer pour la capture vidéo."""
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! video/x-raw, format=(string)BGR ! appsink"
        % (capture_width, capture_height, framerate, flip_method, display_width, display_height)
    )

# ---------------- Fonctions Principales ----------------

previous_label_counts = Counter()
results_file = "detection_results.json"
previous_weight = 0
weight_threshold = 5  # Seuil de changement de poids en grammes

def load_previous_results():
    """Charge les résultats précédents depuis un fichier JSON."""
    global previous_label_counts
    try:
        with open(results_file, "r") as f:
            previous_label_counts = Counter(json.load(f))
            print("Résultats précédents chargés depuis le fichier.")
    except FileNotFoundError:
        print("Fichier de résultats précédents non trouvé. Initialisation vide.")
        previous_label_counts = Counter()
    except json.JSONDecodeError as e:
        print(f"Erreur de lecture du fichier JSON : {e}. Réinitialisation des résultats.")
        previous_label_counts = Counter()

def save_current_results(label_counts):
    """Sauvegarde les résultats actuels dans un fichier JSON."""
    try:
        with open(results_file, "w") as f:
            json.dump(label_counts, f)
            print("Résultats actuels sauvegardés dans le fichier.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des résultats : {e}")

def capture_screen_and_process(mqtt_client):
    """Capture une image de la caméra avec GStreamer, détecte les objets, et publie via MQTT."""
    global previous_label_counts

    cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Impossible d'ouvrir la caméra.")
        return

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Erreur lors de la capture de l'image.")
        return

    # Détection d'objets
    detections = OBJECT_DETECTOR.detect(frame)

    # Filtrer et compter les labels d'intérêt
    labels_of_interest = ['bottle', 'toothbrush', 'banana']
    filtered_labels = [detection['label'] for detection in detections if detection['label'] in labels_of_interest]
    label_counts = Counter(filtered_labels)

    # Calculer la différence avec le comptage précédent
    label_diff = {label: label_counts[label] - previous_label_counts[label] for label in labels_of_interest}

    # Préparer la charge utile JSON
    detections_str = [
        {"label": l, "count": c, "difference": label_diff[l]} 
        for l, c in label_counts.items()
    ]
    mqtt_payload = json.dumps(detections_str)

    # Publier via MQTT
    mqtt_client.publish(MQTT_TOPIC_READ, mqtt_payload)
    print(f"Publié sur MQTT : {mqtt_payload}")

    # Sauvegarder les comptages actuels
    save_current_results(label_counts)

    # Mettre à jour les comptages précédents
    previous_label_counts = label_counts

def on_weight_change(client, userdata, message):
    """Callback exécuté lorsqu'un changement de poids est détecté."""
    global previous_weight

    try:
        payload = json.loads(message.payload.decode("utf-8"))
        current_weight = payload.get("weight", 0)

        # Vérifier le changement de poids
        if abs(current_weight - previous_weight) >= weight_threshold:
            print(f"Changement de poids détecté : {current_weight}g (ancien : {previous_weight}g)")
            previous_weight = current_weight

            # Déclencher le script YOLO
            capture_screen_and_process(client)
    except Exception as e:
        print(f"Erreur dans le traitement du message MQTT : {e}")

# ---------------- Exécution ----------------

if __name__ == "__main__":
    load_previous_results()
    mqtt_client = initialize_mqtt()

    # S'abonner au sujet de la balance
    mqtt_client.subscribe(MQTT_TOPIC_WEIGHT)
    mqtt_client.message_callback_add(MQTT_TOPIC_WEIGHT, on_weight_change)

    try:
        # Boucle principale MQTT
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("Arrêt par l'utilisateur.")
    finally:
        print("Programme terminé proprement.")
