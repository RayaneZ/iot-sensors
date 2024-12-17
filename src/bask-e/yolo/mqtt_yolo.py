import cv2
import numpy as np
import json
from elements.yolo import OBJ_DETECTION
import paho.mqtt.client as mqtt
import requests
import time

# ---------------- Configuration ----------------

# UI Display Control
SHOW_UI = False

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
OBJECT_DETECTOR = OBJ_DETECTION('weights/yolov5s.pt', OBJECT_CLASSES)

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_READ = "camera/objects/detected"

# Thingsboard Configuration
THINGSBOARD_BASE_URL = "https://iot-5etoiles.bnf.sigl.epita.fr"
TOKEN = "muOVFVkq5YWhvpGoSmJq"
ATTRIBUTE_URL = f"{THINGSBOARD_BASE_URL}/api/plugins/telemetry/ASSET/495a4310-a810-11ef-8ecc-15f62f1e4cc0/values/attributes"

# ---------------- Initialisation ----------------

def initialize_mqtt():
    """Initialise et connecte le client MQTT."""
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"Erreur de connexion MQTT : {e}")
        exit(1)
    return client

def check_product_reference(detected_label):
    """Vérifie si l'objet détecté est dans le référentiel produit.
    
    Args:
        detected_label (str): Le label de l'objet détecté
        
    Returns:
        tuple: (bool, dict) - (True si l'objet est dans le référentiel, le produit trouvé)
    """
    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = requests.get(ATTRIBUTE_URL, headers=headers)
        if response.status_code == 200:
            products = [item['value'] for item in response.json()]
            for product in products:
                if product.get('category', '').lower() == detected_label.lower():
                    return True, product
        return False, None
    except Exception as e:
        print(f"Erreur lors de la vérification du référentiel : {e}")
        return False, None

def gstreamer_pipeline(capture_width=1920, capture_height=1080, display_width=960,
                       display_height=540, framerate=10, flip_method=2):
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

def draw_detections(frame, detections):
    """Dessine les détections d'objets sur le frame."""
    for obj in detections:
        label = obj['label']
        score = obj['score']
        [(xmin, ymin), (xmax, ymax)] = obj['bbox']
        color = OBJECT_COLORS[OBJECT_CLASSES.index(label)].tolist()
        
        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), color, 2)
        cv2.putText(frame, f'{label} ({score:.2f})', (xmin, ymin - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 1, cv2.LINE_AA)
    return frame

def process_frame(frame, mqtt_client):
    """Traite un frame vidéo : détecte les objets et publie sur MQTT."""
    detections = OBJECT_DETECTOR.detect(frame)
    validated_detections = []
    telemetry_status = True

    for detection in detections:
        is_valid, product = check_product_reference(detection['label'])
        if is_valid:
            detection['product_info'] = product
            validated_detections.append(detection)
        else:
            telemetry_status = False
            print(f"Objet non trouvé dans le référentiel : {detection['label']}")

    mqtt_payload = json.dumps({
        'detections': validated_detections,
        'telemetry_status': telemetry_status,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
    }, indent=4, ensure_ascii=False)
    
    mqtt_client.publish(MQTT_TOPIC_READ, mqtt_payload)
    return validated_detections

# ---------------- Boucle Principale ----------------

def main():
    """Boucle principale : acquisition vidéo, traitement et affichage."""
    mqtt_client = initialize_mqtt()
    cap = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Impossible d'ouvrir la caméra.")
        return

    if SHOW_UI:
        cv2.namedWindow("CSI Camera", cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Erreur de lecture vidéo.")
                break

            # Détection et traitement
            detections = process_frame(frame, mqtt_client)
            
            if SHOW_UI:
                frame = draw_detections(frame, detections)
                cv2.imshow("CSI Camera", frame)

                # Quitter avec la touche 'q'
                if cv2.waitKey(30) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        print("Arrêt par l'utilisateur.")

    finally:
        # Libération des ressources
        cap.release()
        if SHOW_UI:
            cv2.destroyAllWindows()
        print("Programme terminé proprement.")

# ---------------- Exécution ----------------
if __name__ == "__main__":
    main()
