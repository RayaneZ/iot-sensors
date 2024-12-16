#!/bin/bash

# Vérifie si le script est exécuté en tant que root
if [ "$EUID" -ne 0 ]; then
    echo "Veuillez exécuter ce script en tant que root."
    exit 1
fi

# Variables
INSTALL_DIR="/opt/bask-e"
SYSTEMD_DIR="/etc/systemd/system"

# Crée le répertoire d'installation s'il n'existe pas
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Création du répertoire d'installation..."
    mkdir -p "$INSTALL_DIR"
fi

# Copie les fichiers dans le répertoire d'installation
echo "Copie des fichiers dans le répertoire d'installation..."
cp -r * "$INSTALL_DIR/"

# Installation des dépendances Python
echo "Installation des dépendances Python..."
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    python3 -m pip install --upgrade pip
    python3 -m pip install --no-cache-dir -r "$INSTALL_DIR/requirements.txt"
else
    echo "Aucun fichier requirements.txt trouvé, aucune dépendance installée."
fi

# Configuration des services systemd
echo "Configuration des services systemd..."
cp "$INSTALL_DIR/services/etc/systemd/system/"* "$SYSTEMD_DIR/"

# Recharger les services systemd
systemctl daemon-reload

# Activer et démarrer chaque service
echo "Activation et démarrage des services..."
for service in "$SYSTEMD_DIR"/*.service; do
    service_name=$(basename "$service")
    echo "Activation du service : $service_name"
    systemctl enable "$service_name"
    systemctl start "$service_name"
done

echo "Installation terminée avec succès !"
