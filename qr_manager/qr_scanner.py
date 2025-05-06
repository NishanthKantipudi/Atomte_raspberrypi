import cv2
from pyzbar.pyzbar import decode
import json
import os
import time
import firebase_admin
from firebase_admin import credentials, db
import logging

# ==== Setup ====
cwd = os.getcwd()
SECRETS_DIR = os.path.join(cwd, "../secrets")
USER_FILES_PATH = os.path.join(cwd, "user_files.json")
DETAILS_PATH = os.path.join(SECRETS_DIR, "details.json")
KEY_PATH = os.path.join(SECRETS_DIR, "key.json")

# ==== Logging ====
def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

logger = setup_logger()

# ==== Firebase Initialization ====
cred = credentials.Certificate(KEY_PATH)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'storageBucket': 'skilldevelopmentapp.appspot.com'
})
ref = db.reference('Printers')

# ==== Load Device Details ====
with open(DETAILS_PATH, 'r') as f:
    data1 = json.load(f)

# ==== Helpers ====
def load_user_files():
    if not os.path.exists(USER_FILES_PATH) or os.path.getsize(USER_FILES_PATH) == 0:
        return {}
    try:
        with open(USER_FILES_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning("user_files.json is corrupted or empty. Starting with empty data.")
        return {}

def save_user_files(data):
    with open(USER_FILES_PATH, "w") as f:
        json.dump(data, f)

# ==== QR Code Reading ====
def read_qrcode_opencv():
    qr_detector = cv2.QRCodeDetector()
    cap = cv2.VideoCapture(0)

    logger.info("Press 'q' to quit.")
    while True:
        data = load_user_files()
        try:
            ret, frame = cap.read()
            if not ret:
                logger.info("Failed to capture frame. Exiting...")
                break

            detected_barcodes = decode(frame)
            qdata = ""
            for barcode in detected_barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                logger.info(f"Detected {barcode_type}: {barcode_data}")
                qdata = barcode_data

            if qdata[::-1] in data:
                logger.info(data[qdata[::-1]])
                ref.child(str(data1["code"])).child("printstodo").push().set({
                    "user": qdata[::-1],
                    "files": ",".join(data[qdata[::-1]])
                })
                del data[qdata[::-1]]
                save_user_files(data)

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error: {str(e)}")

    cap.release()

# ==== Barcode Reading ====
def read_barcode(device_path="/dev/hidraw0"):
    HID = {
        4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e', 9: 'f',
        10: 'g', 11: 'h', 12: 'i', 13: 'j', 14: 'k', 15: 'l',
        16: 'm', 17: 'n', 18: 'o', 19: 'p', 20: 'q', 21: 'r',
        22: 's', 23: 't', 24: 'u', 25: 'v', 26: 'w', 27: 'x',
        28: 'y', 29: 'z', 30: '1', 31: '2', 32: '3', 33: '4',
        34: '5', 35: '6', 36: '7', 37: '8', 38: '9', 39: '0',
        44: ' ', 45: '-', 46: '=', 47: '[', 48: ']', 49: '\\',
        51: ';', 52: "'", 53: '`', 54: ',', 55: '.', 56: '/'
    }
    SHIFT_HID = {
        4: 'A', 5: 'B', 6: 'C', 7: 'D', 8: 'E', 9: 'F',
        10: 'G', 11: 'H', 12: 'I', 13: 'J', 14: 'K', 15: 'L',
        16: 'M', 17: 'N', 18: 'O', 19: 'P', 20: 'Q', 21: 'R',
        22: 'S', 23: 'T', 24: 'U', 25: 'V', 26: 'W', 27: 'X',
        28: 'Y', 29: 'Z', 30: '!', 31: '@', 32: '#', 33: '$',
        34: '%', 35: '^', 36: '&', 37: '*', 38: '(', 39: ')',
        44: ' ', 45: '_', 46: '+', 47: '{', 48: '}', 49: '|',
        51: ':', 52: '"', 53: '~', 54: '<', 55: '>', 56: '?'
    }

    barcode = ""
    with open(device_path, 'rb') as fp:
        while True:
            buffer = fp.read(8)
            if buffer[2] == 40:  # Enter key
                break
            if buffer[0] == 2:
                key = SHIFT_HID.get(buffer[2], '')
            else:
                key = HID.get(buffer[2], '')
            barcode += key

    logger.info(f"Scanned barcode: {barcode}")

    barcode = barcode.translate(str.maketrans({
        ')': '1', '!': '2', '@': '3', '#': '4', '$': '5',
        '%': '6', '^': '7', '&': '8', '*': '9', '(': '0'
    }))
    logger.info(f"Corrected barcode: {barcode}")
    return barcode

# ==== Main Execution ====
if __name__ == "__main__":
    while True:
        data = load_user_files()
        value = read_barcode()
        if value in data:
            logger.info(data[value])
            uid = db.reference('user_mappings').child(value).get()
            ref.child(str(data1["code"])).child("printstodo").push().set({
                "user": uid,
                "files": ",".join(data[value])
            })
            del data[value]
            save_user_files(data)

# To run QR code scanning instead of barcode:
# if __name__ == "__main__":
#     read_qrcode_opencv()
