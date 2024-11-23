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

load_dotenv()
QRCODE_CONNECTION_MODULE_PORT = int(os.getenv('QRCODE_CONNECTION_MODULE_PORT'))



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


def scan_qr_code():
    """
    Active la caméra pour lire les QR codes en mode hors ligne.
    """
    global frame_count
    print("[INFO] Mode hors ligne activé : Lecture de QR code")
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
            cv2.imshow("Mode Hors Ligne - QR Code Scanner", frame)
            key = cv2.waitKey(1) & 0xFF

            # Si l'utilisateur appuie sur 'q', quitter
            if key == ord('q'):
                print("[INFO] Quitter le mode hors ligne")
                break

            # Traite les QR codes détectés
            for barcode in barcodes:
                barcode_data = barcode.data.decode("utf-8")
                barcode_type = barcode.type
                print(f"[INFO] Détecté : {barcode_data} ({barcode_type})")

                # Dessine un cadre autour du QR code
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

                # Capture l'image si nécessaire
                frame_count += 1
                filename = f"frame_{frame_count}.jpg"
                cv2.imwrite(filename, frame)
                print(f"[INFO] Image sauvegardée sous : {filename}")

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


@app.route("/scan", methods=["POST"])
def manual_scan():
    """
    Endpoint pour forcer une lecture de QR code (mode manuel).
    """
    scan_qr_code()
    return jsonify({"status": "QR code scanning completed"})


if __name__ == "__main__":
    # Vérifie la connectivité
    if is_connected():
        print("[INFO] Internet détecté, démarrage du microservice HTTP")
        app.run(host="0.0.0.0", port=QRCODE_CONNECTION_MODULE_PORT, debug=False)
    else:
        # Mode hors ligne : Lecture de QR code
        scan_qr_code()
