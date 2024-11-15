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


FW_CHECKSUM_ATTR = "fw_checksum"
FW_CHECKSUM_ALG_ATTR = "fw_checksum_algorithm"
FW_SIZE_ATTR = "fw_size"
FW_TITLE_ATTR = "fw_title"
FW_VERSION_ATTR = "fw_version"

FW_STATE_ATTR = "fw_state"

REQUIRED_SHARED_KEYS = [FW_CHECKSUM_ATTR, FW_CHECKSUM_ALG_ATTR, FW_SIZE_ATTR, FW_TITLE_ATTR, FW_VERSION_ATTR]


def collect_required_data():
    config = { 
        "host": "iot-5etoiles.bnf.sigl.epita.fr", 
        "token": "muOVFVkq5YWhvpGoSmJq", 
        "chunk_size": 0 
    }
    return config


def send_telemetry(telemetry):
    print(f"Sending current info: {telemetry}")
    post(f"https://{config['host']}/api/v1/{config['token']}/telemetry",json=telemetry)


def get_firmware_info():
    response = get(f"https://{config['host']}/api/v1/{config['token']}/attributes", params={"sharedKeys": REQUIRED_SHARED_KEYS}).json()
    return response.get("shared", {})


def get_firmware(fw_info):
    chunk_count = ceil(fw_info.get(FW_SIZE_ATTR, 0)/config["chunk_size"]) if config["chunk_size"] > 0 else 0
    firmware_data = b''
    for chunk_number in range (chunk_count + 1):
        params = {
            "title": fw_info.get(FW_TITLE_ATTR),
            "version": fw_info.get(FW_VERSION_ATTR),
            "size": config["chunk_size"] if config["chunk_size"] < fw_info.get(FW_SIZE_ATTR, 0) else fw_info.get(FW_SIZE_ATTR, 0),
            "chunk": chunk_number
        }

        print(params)
        print(f'Getting chunk with number: {chunk_number + 1}. Chunk size is : {config["chunk_size"]} byte(s).')
        print(f"https://{config['host']}/api/v1/{config['token']}/firmware", params)
        response = get(f"https://{config['host']}/api/v1/{config['token']}/firmware", params=params)
        if response.status_code != 200:
            print("Received error:")
            response.raise_for_status()
            return
        firmware_data = firmware_data + response.content
    return firmware_data


def verify_checksum(firmware_data, checksum_alg, checksum):
    if firmware_data is None:
        print("Firmware wasn't received!")
        return False
    if checksum is None:
        print("Checksum was't provided!")
        return False
    checksum_of_received_firmware = None
    print(f"Checksum algorithm is: {checksum_alg}")
    if checksum_alg.lower() == "sha256":
        checksum_of_received_firmware = sha256(firmware_data).digest().hex()
    elif checksum_alg.lower() == "sha384":
        checksum_of_received_firmware = sha384(firmware_data).digest().hex()
    elif checksum_alg.lower() == "sha512":
        checksum_of_received_firmware = sha512(firmware_data).digest().hex()
    elif checksum_alg.lower() == "md5":
        checksum_of_received_firmware = md5(firmware_data).digest().hex()
    elif checksum_alg.lower() == "murmur3_32":
        reversed_checksum = f'{hash(firmware_data, signed=False):0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_firmware = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    elif checksum_alg.lower() == "murmur3_128":
        reversed_checksum = f'{hash128(firmware_data, signed=False):0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_firmware = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    elif checksum_alg.lower() == "crc32":
        reversed_checksum = f'{crc32(firmware_data) & 0xffffffff:0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_firmware = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    else:
        print("Client error. Unsupported checksum algorithm.")
    print(checksum_of_received_firmware)
    random_value = randint(0, 5)
    if random_value > 3:
        print("Dummy fail! Do not panic, just restart and try again the chance of this fail is ~20%")
        return False
    return checksum_of_received_firmware == checksum


def dummy_upgrade(version_from, version_to):
    print(f"Updating from {version_from} to {version_to}:")
    
    # Create temp directory for update
    temp_dir = "/tmp/ota_update"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Extract update package
        print("Extracting update package...")
        with zipfile.ZipFile(firmware_info.get(FW_TITLE_ATTR), 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Restart service to apply update
        print("Restarting service...")
        subprocess.run(["sudo", "systemctl", "restart", "ota_update.service"], check=True)
        
        print(f"Firmware updated successfully to version {version_to}")
        
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
    current_firmware_info = {
        "current_fw_title": None,
        "current_fw_version": None
    }
    send_telemetry(current_firmware_info)

    print(f"Getting firmware info from {config['host']}..")
    while True:

        firmware_info = get_firmware_info()

        if (firmware_info.get(FW_VERSION_ATTR) is not None and firmware_info.get(FW_VERSION_ATTR) != current_firmware_info.get("current_" + FW_VERSION_ATTR)) \
                or (firmware_info.get(FW_TITLE_ATTR) is not None and firmware_info.get(FW_TITLE_ATTR) != current_firmware_info.get("current_" + FW_TITLE_ATTR)):
            print("New firmware available!")

            current_firmware_info[FW_STATE_ATTR] = "DOWNLOADING"
            sleep(1)
            send_telemetry(current_firmware_info)

            firmware_data = get_firmware(firmware_info)

            current_firmware_info[FW_STATE_ATTR] = "DOWNLOADED"
            sleep(1)
            send_telemetry(current_firmware_info)

            verification_result = verify_checksum(firmware_data, firmware_info.get(FW_CHECKSUM_ALG_ATTR), firmware_info.get(FW_CHECKSUM_ATTR))

            if verification_result:
                print("Checksum verified!")
                current_firmware_info[FW_STATE_ATTR] = "VERIFIED"
                sleep(1)
                send_telemetry(current_firmware_info)
            else:
                print("Checksum verification failed!")
                current_firmware_info[FW_STATE_ATTR] = "FAILED"
                sleep(1)
                send_telemetry(current_firmware_info)
                firmware_data = get_firmware(firmware_info)
                continue

            current_firmware_info[FW_STATE_ATTR] = "UPDATING"
            sleep(1)
            send_telemetry(current_firmware_info)

            with open(firmware_info.get(FW_TITLE_ATTR), "wb") as firmware_file:
                firmware_file.write(firmware_data)

            dummy_upgrade(current_firmware_info["current_" + FW_VERSION_ATTR], firmware_info.get(FW_VERSION_ATTR))

            current_firmware_info = {
                "current_" + FW_TITLE_ATTR: firmware_info.get(FW_TITLE_ATTR),
                "current_" + FW_VERSION_ATTR: firmware_info.get(FW_VERSION_ATTR),
                FW_STATE_ATTR: "UPDATED"
            }
            sleep(1)
            send_telemetry(current_firmware_info)
        sleep(1)