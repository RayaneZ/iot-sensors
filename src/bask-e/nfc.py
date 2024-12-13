from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *
from flask import Flask, jsonify, request
from datetime import datetime
import json

app = Flask(__name__)

# Initialisation du lecteur NFC
pn = Pn532_i2c()
pn.SAMconfigure()

def format_card_data(data):
    """Convertit les données de la carte en format JSON"""
    try:
        return json.loads(data.decode('utf-8'))
    except:
        return {
            "raw_hex": data.hex(),
            "blocks": [
                {
                    "block": i,
                    "data": data[i:i+4].hex()
                } for i in range(0, len(data), 4)
            ]
        }

@app.route('/api/nfc/read', methods=['GET'])
def read_nfc():
    try:
        card_data = pn.read_mifare().get_data()
        formatted_data = format_card_data(card_data)
        return jsonify({
            'success': True,
            'data': formatted_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/nfc/write', methods=['POST'])
def write_nfc():
    try:
        # Vérification du contenu de la requête
        if not request.is_json:
            raise ValueError("Le contenu doit être en JSON")
        
        content = request.get_json()
        if 'data' not in content:
            raise ValueError("Le champ 'data' est requis")

        data = content['data']
        block = content.get('block', 1)  # Block par défaut = 1
        
        # Conversion des données en bytes si nécessaire
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')
            
        # Vérification de la taille des données (16 bytes max par bloc)
        if len(data) > 16:
            raise ValueError("Les données ne doivent pas dépasser 16 bytes")
            
        # Authentification avec la carte (clé par défaut)
        key = b'\xFF\xFF\xFF\xFF\xFF\xFF'
        pn.mifare_auth(block, key)
        
        # Écriture des données
        pn.mifare_write(block, data)
        
        return jsonify({
            'success': True,
            'message': 'Données écrites avec succès',
            'block': block,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)