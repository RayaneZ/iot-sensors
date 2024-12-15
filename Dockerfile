# Utiliser une image de base Python
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier le fichier requirements.txt et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source dans le conteneur
COPY src/bask-e/ .

# Commande par défaut pour exécuter votre script
CMD ["python", "scale.py"]