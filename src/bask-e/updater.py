from requests import get, post
from time import sleep
from zlib import crc32
from hashlib import sha256, sha384, sha512, md5
from mmh3 import hash, hash128
from math import ceil
from random import randint
import zipfile
import os
import subprocess
import threading


SW_CHECKSUM_ATTR = "sw_checksum"
SW_CHECKSUM_ALG_ATTR = "sw_checksum_algorithm"
SW_SIZE_ATTR = "sw_size"
SW_TITLE_ATTR = "sw_title"
SW_VERSION_ATTR = "sw_version"

SW_STATE_ATTR = "sw_state"

REQUIRED_SHARED_KEYS = [SW_CHECKSUM_ATTR, SW_CHECKSUM_ALG_ATTR, SW_SIZE_ATTR, SW_TITLE_ATTR, SW_VERSION_ATTR]


def collect_required_data():
    config = { 
        "host": "iot-5etoiles.bnf.sigl.epita.fr", 
        "token": "muOVFVkq5YWhvpGoSmJq", 
        "chunk_size": 0,
        "username": "sysadmin@thingsboard.org",
        "password": "sysadmin5etoilesiot"
    }
    return config


def get_auth_token():
    response = post(f"https://{config['host']}/api/auth/login", 
                   json={
                       "username": config["username"],
                       "password": config["password"]
                   })
    return response.json().get("token")


def send_online_status(auth_token):
    while True:
        headers = {"Authorization": f"Bearer {auth_token}"}
        post(f"https://{config['host']}/api/v1/{config['token']}/telemetry",
             headers=headers,
             json={"status": "online"})
        sleep(10)


def send_telemetry(telemetry):
    print(f"Sending current info: {telemetry}")
    post(f"https://{config['host']}/api/v1/{config['token']}/telemetry",json=telemetry)


def get_software_info():
    response = get(f"https://{config['host']}/api/v1/{config['token']}/attributes", params={"sharedKeys": REQUIRED_SHARED_KEYS}).json()
    return response.get("shared", {})


def get_software(sw_info):
    chunk_count = ceil(sw_info.get(SW_SIZE_ATTR, 0)/config["chunk_size"]) if config["chunk_size"] > 0 else 0
    software_data = b''
    for chunk_number in range (chunk_count + 1):
        params = {
            "title": sw_info.get(SW_TITLE_ATTR),
            "version": sw_info.get(SW_VERSION_ATTR),
            "size": config["chunk_size"] if config["chunk_size"] < sw_info.get(SW_SIZE_ATTR, 0) else sw_info.get(SW_SIZE_ATTR, 0),
            "chunk": chunk_number
        }

        print(params)
        print(f'Getting chunk with number: {chunk_number + 1}. Chunk size is : {config["chunk_size"]} byte(s).')
        print(f"https://{config['host']}/api/v1/{config['token']}/software", params)
        response = get(f"https://{config['host']}/api/v1/{config['token']}/software", params=params)
        if response.status_code != 200:
            print("Received error:")
            response.raise_for_status()
            return
        software_data = software_data + response.content
    return software_data


def verify_checksum(software_data, checksum_alg, checksum):
    if software_data is None:
        print("Software wasn't received!")
        return False
    if checksum is None:
        print("Checksum was't provided!")
        return False
    checksum_of_received_software = None
    print(f"Checksum algorithm is: {checksum_alg}")
    if checksum_alg.lower() == "sha256":
        checksum_of_received_software = sha256(software_data).digest().hex()
    elif checksum_alg.lower() == "sha384":
        checksum_of_received_software = sha384(software_data).digest().hex()
    elif checksum_alg.lower() == "sha512":
        checksum_of_received_software = sha512(software_data).digest().hex()
    elif checksum_alg.lower() == "md5":
        checksum_of_received_software = md5(software_data).digest().hex()
    elif checksum_alg.lower() == "murmur3_32":
        reversed_checksum = f'{hash(software_data, signed=False):0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_software = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    elif checksum_alg.lower() == "murmur3_128":
        reversed_checksum = f'{hash128(software_data, signed=False):0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_software = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    elif checksum_alg.lower() == "crc32":
        reversed_checksum = f'{crc32(software_data) & 0xffffffff:0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_software = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    else:
        print("Client error. Unsupported checksum algorithm.")
    print(checksum_of_received_software)
    random_value = randint(0, 5)
    if random_value > 3:
        print("Dummy fail! Do not panic, just restart and try again the chance of this fail is ~20%")
        return False
    return checksum_of_received_software == checksum


def dummy_upgrade(version_from, version_to):
    print(f"Updating from {version_from} to {version_to}:")
    
    # Create temp directory for update
    temp_dir = "/tmp/ota_update"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Extract update package
        print("Extracting update package...")
        with zipfile.ZipFile(software_info.get(SW_TITLE_ATTR), 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    
        # Add permissions and execute the install.sh
        print("Adding permissions and executing the install.sh...")
        subprocess.run(["sudo", "chmod", "+x", temp_dir + "/install.sh"])
        subprocess.run(["sudo", temp_dir + "/install.sh"], check=True)

        # Restart service to apply update
        print("Restarting service...")
        subprocess.run(["sudo", "systemctl", "restart", "ota_update.service"], check=True)
        
        print(f"Software updated successfully to version {version_to}")
        
    except Exception as e:
        print(f"Error during upgrade: {str(e)}")
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            subprocess.run(["sudo", "rm", "-rf", temp_dir])
    
    return True


if __name__ == '__main__':
    config = collect_required_data()
    
    # Get initial auth token and start status thread
    auth_token = get_auth_token()
    status_thread = threading.Thread(target=send_online_status, args=(auth_token,))
    status_thread.daemon = True
    status_thread.start()
    
    # Initialiser les informations du software actuel
    current_software_info = {
        "current_sw_title": None,
        "current_sw_version": None
    }
    send_telemetry(current_software_info)

    print(f"Getting software info from {config['host']}..")
    while True:
        software_info = get_software_info()
        
        # Vérifier si une nouvelle version est disponible en comparant avec la version actuelle
        new_version_available = False
        if software_info.get(SW_VERSION_ATTR) and software_info.get(SW_TITLE_ATTR):
            if current_software_info.get("current_" + SW_VERSION_ATTR) != software_info.get(SW_VERSION_ATTR) or \
               current_software_info.get("current_" + SW_TITLE_ATTR) != software_info.get(SW_TITLE_ATTR):
                new_version_available = True

        if new_version_available:
            print("New software available!")

            current_software_info[SW_STATE_ATTR] = "DOWNLOADING"
            sleep(1)
            send_telemetry(current_software_info)

            software_data = get_software(software_info)

            current_software_info[SW_STATE_ATTR] = "DOWNLOADED"
            sleep(1)
            send_telemetry(current_software_info)

            verification_result = verify_checksum(software_data, software_info.get(SW_CHECKSUM_ALG_ATTR), software_info.get(SW_CHECKSUM_ATTR))

            if verification_result:
                print("Checksum verified!")
                current_software_info[SW_STATE_ATTR] = "VERIFIED"
                sleep(1)
                send_telemetry(current_software_info)
            else:
                print("Checksum verification failed!")
                current_software_info[SW_STATE_ATTR] = "FAILED"
                sleep(1)
                send_telemetry(current_software_info)
                software_data = get_software(software_info)
                continue

            current_software_info[SW_STATE_ATTR] = "UPDATING"
            sleep(1)
            send_telemetry(current_software_info)

            with open(software_info.get(SW_TITLE_ATTR), "wb") as software_file:
                software_file.write(software_data)

            dummy_upgrade(current_software_info["current_" + SW_VERSION_ATTR], software_info.get(SW_VERSION_ATTR))

            current_software_info = {
                "current_" + SW_TITLE_ATTR: software_info.get(SW_TITLE_ATTR),
                "current_" + SW_VERSION_ATTR: software_info.get(SW_VERSION_ATTR),
                SW_STATE_ATTR: "UPDATED"
            }
            sleep(1)
            send_telemetry(current_software_info)
        sleep(10)  # Attendre 10 secondes avant de vérifier à nouveau