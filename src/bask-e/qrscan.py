from flask import Flask, jsonify, request
from imutils.video import VideoStream
from pyzbar import pyzbar
from dotenv import load_dotenv
import imutils
import datetime
import time
import cv2
import os
import subprocess
import json

# Charger les variables d'environnement
load_dotenv()
QRCODE_CONNECTION_MODULE_PORT = int(os.getenv('QRCODE_CONNECTION_MODULE_PORT', 5000))  # Port par défaut: 5000

app = Flask(__name__)
vs = None  # Initialisation du flux vidéo global
frame_count = 0  # Compteur global pour les captures d'image


def is_connected():
    """
    Vérifie si la carte est connectée à Internet.
    """
    try:
        subprocess.check_call(["ping", "-c", "1", "8.8.8.8"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def connect_to_wifi_ionis(username, password):
    """
    Configure et connecte la Jetson Nano au réseau IONIS (Protected EAP - PEAP).
    """
    try:
        # Crée ou met à jour le fichier de configuration wpa_supplicant
        config = f"""
        network={{
            ssid="IONIS"
            key_mgmt=WPA-EAP
            eap=PEAP
            identity="{username}"
            password="{password}"
            phase2="auth=MSCHAPV2"
            ca_cert="N/A"
        }}
        """
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "a") as file:
            file.write(config)
        
        # Redémarre le service réseau pour appliquer les changements
        subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], check=True)
        print(f"[INFO] Tentative de connexion au réseau 'IONIS' initiée.")
        return {"status": "success", "message": "Connecting to IONIS network"}
    except Exception as e:
        print(f"[ERROR] Impossible de se connecter au réseau IONIS : {e}")
        return {"status": "error", "message": str(e)}


def scan_qr_code_and_connect():
    """
    Active la caméra pour lire les QR codes et tenter une connexion (Wi-Fi ou IONIS).
    """
    global frame_count
    print("[INFO] Lecture de QR code pour connexion")
    vs = VideoStream(src=0).start()  # Démarre la caméra
    time.sleep(2.0)  # Laisser le temps à la caméra de chauffer

    try:
        while True:
            # Capture une image et la redimensionne
            frame = vs.read()
            frame = imutils.resize(frame, width=400)

            # Détecte les QR codes dans l'image
            barcodes = pyzbar.decode(frame)

            # Montre l'image en live
            cv2.imshow("QR Code Scanner - Configuration Réseau", frame)
            key = cv2.waitKey(1) & 0xFF

            # Si l'utilisateur appuie sur 'q', quitter
            if key == ord('q'):
                print("[INFO] Quitter le mode lecture QR code")
                break

            # Traite les QR codes détectés
            for barcode in barcodes:
                barcode_data = barcode.data.decode("utf-8")
                print(f"[INFO] QR Code détecté : {barcode_data}")

                try:
                    # Interprète les données comme JSON
                    network_info = json.loads(barcode_data)

                    if "ionis" in network_info:
                        # Connexion au réseau IONIS
                        username = network_info["ionis"].get("username")
                        password = network_info["ionis"].get("password")
                        if username and password:
                            print(f"[INFO] Tentative de connexion au réseau IONIS avec l'identité '{username}'")
                            result = connect_to_wifi_ionis(username, password)
                            print(result)
                            return result
                        else:
                            print("[ERROR] Informations IONIS invalides dans le QR code.")
                    else:
                        # Connexion Wi-Fi standard
                        ssid = network_info.get("ssid")
                        password = network_info.get("password")
                        if ssid and password:
                            print(f"[INFO] Tentative de connexion au réseau : {ssid}")
                            result = connect_to_wifi(ssid, password)
                            print(result)
                            return result
                        else:
                            print("[ERROR] Informations Wi-Fi invalides dans le QR code.")
                except json.JSONDecodeError:
                    print("[ERROR] QR code ne contient pas de JSON valide.")

    finally:
        # Fermer le flux vidéo
        vs.stop()
        cv2.destroyAllWindows()


@app.route("/status", methods=["GET"])
def status():
    """
    Endpoint pour vérifier l'état de la carte.
    """
    connection_status = is_connected()
    return jsonify({"connected": connection_status})


@app.route("/scan_and_connect", methods=["POST"])
def manual_scan_and_connect():
    """
    Endpoint pour scanner un QR code et tenter une connexion.
    """
    result = scan_qr_code_and_connect()
    return jsonify(result)


if __name__ == "__main__":
    # Vérifie la connectivité
    if is_connected():
        print("[INFO] Internet détecté, démarrage du microservice HTTP")
        app.run(host="0.0.0.0", port=QRCODE_CONNECTION_MODULE_PORT, debug=False)
    else:
        # Mode hors ligne : Lecture de QR code pour configuration réseau
        scan_qr_code_and_connect()
