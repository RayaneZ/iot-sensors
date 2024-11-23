Voici une version mise à jour du README intégrant les fonctionnalités du scanner de QR codes en plus de celles du capteur HX711 :

---

# Microservice pour Capteur de Poids (HX711) et Scanner de QR Codes

Ce microservice expose des endpoints RESTful permettant d’interagir avec :
1. Un **capteur de poids** (HX711) pour mesurer des objets.
2. Une **caméra** pour scanner des QR codes et récupérer leur contenu.

Ces fonctionnalités sont accessibles localement via une API REST.

---

## **Prérequis**

1. **Matériel** :
   - Une carte compatible GPIO (Raspberry Pi, Jetson Nano, etc.).
   - Un capteur de poids HX711.
   - Une caméra compatible (USB ou Raspberry Pi Camera Module).

2. **Logiciels nécessaires** :
   - Python 3.7+.
   - Bibliothèques Python installées :
     ```bash
     pip install flask RPi.GPIO opencv-python imutils pyzbar
     ```
   - La bibliothèque HX711 fournie dans le dossier `libs`.

---

## **Installation**

1. Clonez ou téléchargez ce dépôt.
2. Placez le fichier `HX711.py` dans le répertoire `libs/`.
3. Assurez-vous que votre capteur HX711 et votre caméra sont correctement câblés et connectés.

---

## **Démarrage du Microservice**

1. Lancez le script Python principal :
   ```bash
   python3 microservice.py
   ```

2. Le microservice démarrera sur l’adresse par défaut :
   ```
   http://0.0.0.0:5000
   ```

---

## **Endpoints RESTful**

### **Fonctionnalités du Capteur de Poids (HX711)**

#### **1. Démarrer le Mode Polling**
- **URL** : `/start`
- **Méthode HTTP** : `POST`
- **Description** : Démarre le mode "polling", où les données du capteur sont collectées en continu.

##### Exemple de Requête :
```bash
curl -X POST http://localhost:5000/start
```

##### Exemple de Réponse :
- **Succès** :
  ```json
  {
    "status": "success",
    "message": "Polling started"
  }
  ```
- **Erreur** (si déjà actif) :
  ```json
  {
    "status": "error",
    "message": "Polling is already running"
  }
  ```

---

#### **2. Arrêter le Mode Polling**
- **URL** : `/stop`
- **Méthode HTTP** : `POST`
- **Description** : Arrête le mode "polling".

##### Exemple de Requête :
```bash
curl -X POST http://localhost:5000/stop
```

##### Exemple de Réponse :
- **Succès** :
  ```json
  {
    "status": "success",
    "message": "Polling stopped"
  }
  ```
- **Erreur** (si déjà arrêté) :
  ```json
  {
    "status": "error",
    "message": "Polling is not running"
  }
  ```

---

#### **3. Obtenir le Poids Actuel**
- **URL** : `/weight`
- **Méthode HTTP** : `GET`
- **Description** : Récupère le poids actuellement mesuré par le capteur.

##### Exemple de Requête :
```bash
curl http://localhost:5000/weight
```

##### Exemple de Réponse :
- **Succès** :
  ```json
  {
    "status": "success",
    "weight": 123.45
  }
  ```
- **Erreur** :
  ```json
  {
    "status": "error",
    "message": "Erreur lors de la lecture du capteur"
  }
  ```

---

### **Fonctionnalités du Scanner de QR Codes**

#### **1. Scanner un QR Code**
- **URL** : `/qrscan`
- **Méthode HTTP** : `GET`
- **Description** : Lance le scanner de QR codes et retourne le contenu du code détecté.

##### Exemple de Requête :
```bash
curl http://localhost:5000/qrscan
```

##### Exemple de Réponse :
- **Succès** :
  ```json
  {
    "status": "success",
    "data": "https://example.com"
  }
  ```
- **Erreur** (si aucun code détecté) :
  ```json
  {
    "status": "error",
    "message": "No QR code detected"
  }
  ```

---

## **Arrêt du Microservice**

Pour arrêter le microservice :
- Utilisez `Ctrl + C` dans le terminal où le script est exécuté.
- Cela libérera les broches GPIO et fermera proprement l’application.

---

## **Personnalisation**

1. **Configuration des Broches** :
   - Vous pouvez modifier les broches GPIO utilisées (par défaut, `DOUT=5`, `SCK=6`) dans le script :
     ```python
     DOUT = <numéro_GPIO>
     SCK = <numéro_GPIO>
     ```

2. **Unité de Référence** :
   - Ajustez la variable `referenceUnit` selon votre configuration matérielle et le calibrage :
     ```python
     referenceUnit = <valeur>
     ```

3. **Fréquence de Polling** :
   - Modifiez l’intervalle de lecture dans la fonction `polling_mode()` :
     ```python
     time.sleep(0.1)  # En secondes
     ```

4. **Caméra par Défaut** :
   - Par défaut, la caméra utilisée est accessible via `src=0`. Vous pouvez la modifier dans le script :
     ```python
     vs = VideoStream(src=0).start()
     ```

---

## **Dépannage**

### **Problèmes Courants :**
1. **Erreur GPIO déjà utilisée** :
   - Si le script est arrêté brutalement, utilisez :
     ```bash
     sudo gpio cleanup
     ```

2. **Valeurs Incorrectes pour le Capteur de Poids** :
   - Recalibrez votre capteur HX711 (référez-vous aux commentaires dans le script pour le calibrage).

3. **Scanner de QR Codes ne Fonctionne Pas** :
   - Assurez-vous que la caméra est correctement connectée et fonctionne avec OpenCV :
     ```bash
     python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
     ```

---

## **Contact**

Pour toute question ou assistance, ouvrez une issue sur le dépôt ou contactez le développeur.

--- 

Ce README explique clairement les fonctionnalités des deux services exposés par votre microservice.