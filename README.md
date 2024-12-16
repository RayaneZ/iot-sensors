# Bask-e: Système de Panier Intelligent

Ce projet implémente un système de panier intelligent qui combine plusieurs capteurs et services pour automatiser le processus d'achat.

## Architecture

Le système est composé de plusieurs microservices qui communiquent via MQTT :

- **Balance (HX711)** : Mesure le poids des articles et détecte les changements
- **Lecteur NFC** : Détecte les cartes de paiement et gère le mode paiement
- **Caméra** : Détecte les objets via YOLO pour validation
- **Interface Thingsboard** : Envoie les données du panier et le statut du système

## Prérequis

### Matériel
- Raspberry Pi ou équivalent
- Capteur de poids HX711
- Lecteur NFC
- Caméra USB
- Broker MQTT (ex: Mosquitto)

### Logiciels
- Python 3.7+
- Bibliothèques Python :
  - paho-mqtt
  - gpiod
  - requests
  - flask
  - numpy
  - opencv-python
  - ultralytics