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

ref = db.reference('users')

with open('../secrets/details.json', 'r') as f:
    data1 = json.load(f)


def read_qrcode_opencv():
    # Initialize the QR Code detector
    qr_detector = cv2.QRCodeDetector()
    
    # Open the webcam
    cap = cv2.VideoCapture(0)

    logger.info("Press 'q' to quit.")
    while True:
        with open('user_files.json', 'r') as f:
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
                ref.child(str(data1["code"])).child("printstodo").push().set({"user":data[qdata[::-1]],"files":data[qdata[::-1]]})
                del data[qdata[::-1]]
                open("../files/data.json", "w").write(json.dumps(data))
            time.sleep(0.5)

        except Exception as e:
            logger.info(f"Error: {str(e)}")
    cap.release()

if __name__ == "__main__":
    read_qrcode_opencv()