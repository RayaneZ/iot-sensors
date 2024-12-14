from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *
from flask import Flask, jsonify, request
from datetime import datetime
import json

app = Flask(__name__)

# Initialize NFC reader
pn = Pn532_i2c()
pn.SAMconfigure()

def format_card_data(data):
    """Convert card data to JSON format"""
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)