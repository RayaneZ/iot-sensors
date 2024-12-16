import cv2
import numpy as np
from elements.yolo import OBJ_DETECTION
import paho.mqtt.client as mqtt
import json

SHOW_UI = False

Object_classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
                'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
                'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
                'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
                'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
                'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
                'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
                'hair drier', 'toothbrush' ]

Object_colors = list(np.random.rand(80,3)*255)
Object_detector = OBJ_DETECTION('weights/yolov5s.pt', Object_classes)

refProduit = []
MQTT_BROKER = "localhost"  # Remplacez par l'adresse IP du broker si nécessaire
MQTT_PORT = 1883
MQTT_TOPIC_READ = "camera/objects/detected"
MQTT_TOPIC_PAYMENT_MODE = "camera/payment_mode"
mqtt_client = mqtt.Client()
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print(f"Connecté au broker MQTT : {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"Impossible de se connecter au broker MQTT : {e}")
    exit(1)

def gstreamer_pipeline(
    capture_width=1920,
    capture_height=1080,
    display_width=960,
    display_height=540,
    framerate=10,
    flip_method=2,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

# To flip the image, modify the flip_method parameter (0 and 2 are the most common)
print(gstreamer_pipeline(flip_method=0))
cap = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)
if cap.isOpened():
    if SHOW_UI:
        window_handle = cv2.namedWindow("CSI Camera", cv2.WINDOW_AUTOSIZE)
    
    while True:
        if SHOW_UI and cv2.getWindowProperty("CSI Camera", 0) < 0:
            break
            
        ret, frame = cap.read()
        if ret:
            # detection process
            objs = Object_detector.detect(frame)
            json_data = json.dumps(objs, indent=4, ensure_ascii=False)
            
            if SHOW_UI:
                # plotting
                for obj in objs:
                    label = obj['label']
                    score = obj['score']
                    [(xmin,ymin),(xmax,ymax)] = obj['bbox']
                    color = Object_colors[Object_classes.index(label)]
                    frame = cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), color, 2) 
                    frame = cv2.putText(frame, f'{label} ({str(score)})', (xmin,ymin), cv2.FONT_HERSHEY_SIMPLEX , 0.75, color, 1, cv2.LINE_AA)
            
            mqtt_client.publish(MQTT_TOPIC_READ, json.dumps(objs, indent=4, ensure_ascii=False))

        if SHOW_UI:
            cv2.imshow("CSI Camera", frame)
            keyCode = cv2.waitKey(30)
            if keyCode == ord('q'):
                break
        
    cap.release()
    if SHOW_UI:
        cv2.destroyAllWindows()
else:
    print("Unable to open camera")
