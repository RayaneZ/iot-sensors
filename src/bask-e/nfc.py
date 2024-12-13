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

@app.route('/api/nfc/write', methods=['POST'])
def write_nfc():
    try:
        # Check request content
        if not request.is_json:
            raise ValueError("Content must be JSON")
        
        content = request.get_json()
        if 'data' not in content:
            raise ValueError("Field 'data' is required")

        data = content['data']
        block = content.get('block', 1)  # Default block = 1
        
        # Convert data to bytes if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')
            
        # Check data size (16 bytes max per block)
        if len(data) > 16:
            raise ValueError("Data must not exceed 16 bytes")
            
        # Card authentication (default key)
        key = b'\xFF\xFF\xFF\xFF\xFF\xFF'
        pn.mifare_auth(block, key)
        
        # Write data
        pn.mifare_write(block, data)
        
        return jsonify({
            'success': True,
            'message': 'Data written successfully',
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