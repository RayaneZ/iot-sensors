import time
import sys
import threading
import os
import RPi.GPIO as GPIO
from flask import Flask, jsonify, request
from libs.HX711 import HX711
from dotenv import load_dotenv

load_dotenv()

# Configuration des broches GPIO
DOUT = int(os.getenv('DOUT'))
SCK = int(os.getenv('SCK'))
SCALE_MODULE_PORT = int(os.getenv('SCALE_MODULE_PORT'))

# Modes de lecture
READ_MODE_INTERRUPT_BASED = "interrupt-based"
READ_MODE_POLLING_BASED = "polling-based"
READ_MODE = READ_MODE_INTERRUPT_BASED

# Flask app
app = Flask(__name__)

# HX711 instance
hx = HX711(DOUT, SCK)

# Variables globales
referenceUnit = 114
is_running = False  # Indicate if polling mode is active
polling_thread = None


def setup_hx711():
    """
    Configure le capteur HX711.
    """
    global hx
    hx.setReadingFormat("MSB", "MSB")
    hx.autosetOffset()
    offsetValue = hx.getOffset()
    print(f"[INFO] Offset automatique défini : {offsetValue}")
    hx.setReferenceUnit(referenceUnit)
    print(f"[INFO] Unité de référence définie : {referenceUnit}")


def printAll(rawBytes):
    """
    Callback pour afficher les données en mode interrupt.
    """
    longValue = hx.rawBytesToLong(rawBytes)
    longWithOffsetValue = hx.rawBytesToLongWithOffset(rawBytes)
    weightValue = hx.rawBytesToWeight(rawBytes)
    print(f"[INFO] INTERRUPT_BASED | longValue: {longValue} | longWithOffsetValue: {longWithOffsetValue} | weight (grams): {weightValue}")


def polling_mode():
    """
    Exécute le mode polling.
    """
    global is_running
    while is_running:
        try:
            rawBytes = hx.getRawBytes()
            longValue = hx.rawBytesToLong(rawBytes)
            longWithOffsetValue = hx.rawBytesToLongWithOffset(rawBytes)
            weightValue = hx.rawBytesToWeight(rawBytes)
            print(f"[INFO] POLLING_BASED | longValue: {longValue} | longWithOffsetValue: {longWithOffsetValue} | weight (grams): {weightValue}")
            time.sleep(0.1)  # Réduire la fréquence si nécessaire
        except Exception as e:
            print(f"[ERROR] Polling error: {e}")


@app.route("/start", methods=["POST"])
def start_polling():
    """
    Démarre le mode polling.
    """
    global is_running, polling_thread

    if is_running:
        return jsonify({"status": "error", "message": "Polling is already running"}), 400

    is_running = True
    polling_thread = threading.Thread(target=polling_mode)
    polling_thread.start()
    return jsonify({"status": "success", "message": "Polling started"})


@app.route("/stop", methods=["POST"])
def stop_polling():
    """
    Arrête le mode polling.
    """
    global is_running

    if not is_running:
        return jsonify({"status": "error", "message": "Polling is not running"}), 400

    is_running = False
    polling_thread.join()
    return jsonify({"status": "success", "message": "Polling stopped"})


@app.route("/weight", methods=["GET"])
def get_weight():
    """
    Récupère le poids actuel.
    """
    try:
        rawBytes = hx.getRawBytes()
        weightValue = hx.rawBytesToWeight(rawBytes)
        return jsonify({"status": "success", "weight": weightValue})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Configure le capteur au démarrage
    setup_hx711()

    # Activer le mode interrupt si configuré
    if READ_MODE == READ_MODE_INTERRUPT_BASED:
        print("[INFO] Activation du mode 'interrupt-based'")
        hx.enableReadyCallback(printAll)

    # Démarrage du serveur Flask
    try:
        print("[INFO] Démarrage du microservice")
        app.run(host="0.0.0.0", port=SCALE_MODULE_PORT, debug=False)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("[INFO] Arrêt du microservice et nettoyage des GPIO.")
        sys.exit()
