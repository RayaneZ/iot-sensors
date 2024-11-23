#!/bin/bash

# Fonction pour vérifier si Jetpack est installé
check_jetpack_installed() {
    if [ -f "/etc/nv_tegra_release" ]; then
        echo "Jetpack est déjà installé."
        return 0
    else
        echo "Jetpack n'est pas installé. Veuillez installer Jetpack avant de continuer."
        echo "Vous pouvez télécharger Jetpack via NVIDIA SDK Manager : https://developer.nvidia.com/embedded/jetpack"
        exit 1
    fi
}

# Vérifie si Jetpack est installé
check_jetpack_installed

# Met à jour les paquets
if [ -x "$(command -v apt)" ]; then
    echo "Mise à jour des paquets..."
    sudo apt update && sudo apt upgrade -y
else
    echo "apt n'est pas disponible sur ce système."
    exit 1
fi

# Installe Python et pip si nécessaire
if ! [ -x "$(command -v python3)" ]; then
    echo "Installation de Python3 et pip..."
    sudo apt install python3 python3-pip -y
else
    echo "Python3 est déjà installé."
fi

# Installe les bibliothèques nécessaires avec pip
if [ -x "$(command -v pip3)" ]; then
    echo "Installation des bibliothèques Python nécessaires..."
    pip3 install --upgrade pip
    pip3 install opencv-python imutils pyzbar flask python-dotenv Jetson.GPIO
else
    echo "pip3 n'est pas disponible, veuillez vérifier l'installation de Python."
    exit 1
fi

# Configuration des droits pour Jetson.GPIO
if [ -d "/sys/class/gpio" ]; then
    echo "Configuration des permissions pour Jetson.GPIO..."
    sudo groupadd -f gpio
    sudo usermod -aG gpio $USER
    sudo chmod -R 770 /sys/class/gpio
    echo "Veuillez redémarrer votre session ou exécuter 'newgrp gpio' pour appliquer les changements."
fi

# Installe OpenCV et les dépendances CUDA pour Jetson
echo "Installation des dépendances OpenCV pour Jetson..."
sudo apt install libopencv-dev python3-opencv -y

# Exécute le script Python si présent
if [ -f "qrscan.py" ]; then
    echo "Exécution de qrscan.py..."
    python3 qrscan.py
else
    echo "Le fichier qrscan.py n'a pas été trouvé dans le répertoire actuel."
fi
