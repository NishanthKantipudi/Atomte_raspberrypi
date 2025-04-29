import cv2
from pyzbar.pyzbar import decode
import json
import os,time
import firebase_admin
from firebase_admin import credentials, db
import logging,csv,json
cwd = os.getcwd()
def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()


cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'storageBucket': 'skilldevelopmentapp.appspot.com'
})

ref = db.reference('Printers')

with open(cwd+'/../secrets/details.json', 'r') as f:
    data1 = json.load(f)


def read_qrcode_opencv():
    # Initialize the QR Code detector
    qr_detector = cv2.QRCodeDetector()
    
    # Open the webcam
    cap = cv2.VideoCapture(0)

    logger.info("Press 'q' to quit.")
    while True:
        with open(cwd+'/user_files.json', 'r') as f:
            data = json.load(f)
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
                logger.info(f"QR Code detected: {qdata}")
            if(qdata[::-1] in data):
                logger.info(data[qdata[::-1]])
                ref.child(str(data1["code"])).child("printstodo").push().set({"user":qdata[::-1],"files":",".join(data[qdata[::-1]])})
                del data[qdata[::-1]]
                open(cwd+"/user_files.json", "w").write(json.dumps(data))
            time.sleep(0.5)

        except Exception as e:
            logger.info(f"Error: {str(e)}")
    cap.release()



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
            if buffer[0] == 2:  # Shift key pressed
                key = SHIFT_HID.get(buffer[2], '')
            else:
                key = HID.get(buffer[2], '')
            barcode += key
    
    print(f"Scanned barcode: {barcode}")
        
    print(f"Raw scanned barcode: {barcode}")
    barcode = barcode.translate(str.maketrans({
        ')': '1',
        '!': '2',
        '@': '3',
        '#': '4',
        '$': '5',
        '%': '6',
        '^': '7',
        '&': '8',
        '*': '9',
        '(': '0'
    }))
    print(f"Corrected barcode: {barcode}")
    return barcode

if __name__ == "__main__":
    while True:
        with open(cwd+'/user_files.json', 'r') as f:
            data = json.load(f)
        value=read_barcode()
        if(value in data):
            logger.info(data[value])
            uid=db.reference('user_mappings').child(value).get()
            ref.child(str(data1["code"])).child("printstodo").push().set({"user":uid,"files":",".join(data[value])})
            del data[value]
            open(cwd+"/user_files.json", "w").write(json.dumps(data))


# if __name__ == "__main__":
#     read_qrcode_opencv()

