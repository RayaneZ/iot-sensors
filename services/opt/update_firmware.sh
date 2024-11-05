#!/bin/bash
OTA_ID="$1"
THINGSBOARD_SERVER="https://iot-5etoiles.bnf.sigl.epita.fr"
DEVICE_TOKEN="<TON_TOKEN_D'APPAREIL>"
TMP_FOLDER="/tmp/ota_update"
FILE_NAME="firmware.bin"

# Crée un répertoire temporaire pour la mise à jour
mkdir -p $TMP_FOLDER
cd $TMP_FOLDER

# Télécharger la mise à jour depuis ThingsBoard
wget "$THINGSBOARD_SERVER/api/v1/$DEVICE_TOKEN/firmware/$OTA_ID" -O firmware.bin

# Appliquer la mise à jour (modifie cette ligne selon le type de mise à jour)
chmod +x firmware.bin
./firmware.bin  # Exécute le binaire, ou adapte si c'est un script d'installation

# Nettoyage
rm -rf $TMP_FOLDER
