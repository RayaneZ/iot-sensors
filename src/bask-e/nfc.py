from py532lib.i2c import *
from py532lib.frame import *
from py532lib.constants import *
from datetime import datetime, timedelta
import json
import threading
import time


# Initialize NFC reader
pn = Pn532_i2c()
pn.SAMconfigure()

# Global variables to store last read data
last_read = {
    'data': None,
    'timestamp': None
}

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

def continuous_read():
    global last_read
    while True:
        try:
            card_data = pn.read_mifare().get_data()
            last_read['data'] = format_card_data(card_data)
            last_read['timestamp'] = datetime.now()
        except:
            time.sleep(0.1)  # Small delay to prevent CPU overuse
            continue

if __name__ == '__main__':
    # Start the continuous reading in a separate thread
    read_thread = threading.Thread(target=continuous_read, daemon=True)
    read_thread.start()