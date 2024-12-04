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
        # Capture frame-by-frame
            ret, frame = cap.read()
            if not ret:
                logger.info("Failed to capture frame. Exiting...")
                break
            qdata, bbox, _ = qr_detector.detectAndDecode(frame)
            if bbox is not None and qdata:
                # Convert bounding box points to integers and draw lines
                bbox = bbox.astype(int)
                for i in range(len(bbox[0])):
                    pt1 = tuple(bbox[0][i])
                    pt2 = tuple(bbox[0][(i + 1) % len(bbox[0])])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

                # Display the decoded data
                cv2.putText(frame, qdata, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                logger.info(f"QR Code detected: {qdata}")
                if(qdata[::-1] in data):
                    logger.info(data[qdata[::-1]])
                    ref.child(str(data1["code"])).child("printstodo").push().set({"user":data[qdata[::-1]],"files":data[qdata[::-1]]})
                    del data[qdata[::-1]]
                    open("../files/data.json", "w").write(json.dumps(data))
            # Display the frame
            cv2.imshow("QR Code Scanner", frame)
            time.sleep(1)
            # Break on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        except Exception as e:
            logger.info(f"Error: {str(e)}")
    # Release the webcam and close windows
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    read_qrcode_opencv()