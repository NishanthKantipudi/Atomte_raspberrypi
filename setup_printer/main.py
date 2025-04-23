import subprocess
import threading
import queue
import time
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('printer_setup.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Get configuration paths
CWD = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(CWD, "..", "secrets", "key.json")
DETAILS_PATH = os.path.join(CWD, "..", "..", "secrets", "details.json")
DB_URL = 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/'
STORAGE_BUCKET = 'skilldevelopmentapp.appspot.com'

def load_config():
    """Load configuration data from JSON files"""
    try:
        if not os.path.exists(KEY_PATH) or not os.path.exists(DETAILS_PATH):
            logger.error("Required configuration files not found")
            return None
            
        with open(DETAILS_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return None

def init_firebase():
    """Initialize Firebase connection"""
    try:
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': DB_URL,
            'storageBucket': STORAGE_BUCKET
        })
        logger.info("Firebase initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        return False

def run_command(command, timeout=30):
    """Execute a command with timeout and return results"""
    output_queue = queue.Queue()
    error_queue = queue.Queue()
    
    def execute():
        try:
            logger.info(f"Running: {' '.join(command)}")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            output_queue.put((process.returncode, stdout, stderr))
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            output_queue.put((None, None, str(e)))
    
    thread = threading.Thread(target=execute)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        return None, None, "Command timed out"
    
    try:
        return_code, stdout, stderr = output_queue.get(block=False)
        return return_code, stdout, stderr
    except queue.Empty:
        return None, None, "Failed to get command output"

def get_default_printer_properties():
    """Return default printer properties"""
    return {
        "media": [
            {"name": "iso_a4_210x297mm A4", "value": 0, "cost": 1, "pc": 1},
            {"name": "na_letter_8.5x11in", "value": 0, "cost": 0, "pc": 1},
            {"name": "na_legal_8.5x14in", "value": 0, "cost": 0, "pc": 1},
            {"name": "iso_a3_297x420mm", "value": 0, "cost": 0, "pc": 1},
            {"name": "na_tabloid_11x17in", "value": 0, "cost": 0, "pc": 1},
            {"name": "custom", "value": 0, "cost": 0, "pc": 1}
        ],
        "orientation-requested": [
            {"name": "3 potrait", "value": 0, "cost": 1, "pc": 1},
            {"name": "4 landscape", "value": 0, "cost": 1, "pc": 1}
        ],
        "print_quality": [
            {"name": "draft", "value": 0, "cost": 0, "pc": 1},
            {"name": "normal", "value": 0, "cost": 0, "pc": 1},
            {"name": "high", "value": 0, "cost": 0, "pc": 1},
            {"name": "photo", "value": 0, "cost": 0, "pc": 1}
        ],
        "color_mode": [
            {"name": "color", "value": 0, "cost": 0, "pc": 1},
            {"name": "monochrome", "value": 0, "cost": 0, "pc": 1},
            {"name": "black_and_white", "value": 0, "cost": 1, "pc": 1}
        ],
        "sides": [
            {"name": "one-sided", "value": 1.5, "cost": 1.5, "pc": 1},
            {"name": "two-sided-long-edge", "value": 2, "cost": 2, "pc": 0.5},
            {"name": "two-sided-short-edge", "value": 2, "cost": 2, "pc": 0.5}
        ],
        "number_up": [
            {"name": "1 1_page_per_side", "value": 0, "cost": 0, "pc": 1},
            {"name": "2 2_pages_per_side", "value": 0, "cost": 0, "pc": 1},
            {"name": "4 4_pages_per_side", "value": 0, "cost": 0, "pc": 1},
            {"name": "6 6_pages_per_side", "value": 0, "cost": 0, "pc": 1},
            {"name": "9 9_pages_per_side", "value": 0, "cost": 0, "pc": 1},
            {"name": "16 16_pages_per_side", "value": 0, "cost": 0, "pc": 1}
        ],
        "printer_resolution": [
            {"name": "300x300dpi", "value": 0, "cost": 0, "pc": 1},
            {"name": "600x600dpi", "value": 0, "cost": 0, "pc": 1},
            {"name": "1200x1200dpi", "value": 0, "cost": 0, "pc": 1}
        ],
        "output_bin": [
            {"name": "face-down", "value": 0, "cost": 0, "pc": 1},
            {"name": "face-up", "value": 0, "cost": 0, "pc": 1}
        ]
    }

def setup_printer(data_snapshot):
    """Handle printer setup requests from Firebase"""
    if not data_snapshot.data:
        logger.warning("No setup data provided")
        return
        
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
        
    try:
        # Get printer setup reference
        printer_ref = db.reference("/").child("Printers").child(config["code"]).child("printer_setup_process")
        
        # Check if setup is requested
        if not printer_ref.child("start").get():
            logger.info("No active printer setup process")
            return
            
        # Reset start flag and set initial status
        printer_ref.child("start").set(False)
        printer_ref.child("status").set("connecting")
        
        # Get setup data
        setup_data = printer_ref.get()
        
        # Validate required data
        required_fields = ["printer_ip", "model"]
        missing_fields = [field for field in required_fields if field not in setup_data]
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            printer_ref.child("status").set("failed-missing_data")
            printer_ref.child("connection").set("failed")
            return
            
        # Step 1: Get printer IP and model
        printer_ip = setup_data["printer_ip"]
        printer_model = setup_data["model"]
        printer_name = f"atomte{config['code']}"
        
        logger.info(f"Setting up printer: {printer_name} with IP: {printer_ip}, Model: {printer_model}")
        printer_ref.child("status").set("downloading_driver")
        
        # Step 2: Download PPD file
        ppd_url = f"printers_data/{printer_model}/ppd"
        ppd_path = f"/tmp/{printer_model}.ppd"
        
        ppd_url=db.reference("/").child(ppd_url).get()
        download_result = download_file(ppd_url, ppd_path)
        if not download_result:
            logger.error(f"Failed to download PPD file from {ppd_url}")
            printer_ref.child("status").set("failed-ppd_download")
            printer_ref.child("connection").set("failed")
            return
            
        printer_ref.child("status").set("installing_printer")
        
        # Step 3: Add the printer
        command = [
            "lpadmin",
            "-p", printer_name,
            "-E",
            "-v", f"socket://{printer_ip}:9100",
            "-P", ppd_path
        ]
        
        returncode, stdout, stderr = run_command(command, timeout=30)
        
        if returncode != 0:
            logger.error(f"Printer setup failed: {stderr}")
            printer_ref.child("status").set(f"failed-{stderr}")
            printer_ref.child("connection").set("failed")
            return
            
        logger.info("Printer added successfully")
        printer_ref.child("status").set("configuring_properties")
        
        # Step 4: Fetch and set options
        properties_url = f"printers_data/{printer_model}/properties"
        properties = db.reference("/").child(properties_url).get()
        
        if not properties:
            logger.warning(f"Could not fetch properties from {properties_url}, using defaults")
            properties = get_default_printer_properties()
            
       
        
        # Update properties in Firebase
        for category in properties.values():
            for item in category:
                item["value"] = item["cost"]
                
        # Update Firebase with success status
        printer_ref.child("properties").set(properties)
        printer_ref.child("connection").set("success")
        printer_ref.child("status").set("success")
        
        # Update printer details in the database
        db_ref = db.reference("/").child("Printers").child(config["code"])
        db_ref.child("printer_setup").set(True)
        db_ref.child("select_properties").set(True)
        
        # Update printer details
        details_to_update = {
            "ip": setup_data.get("printer_ip", ""),
            "name": setup_data.get("name", ""),
            "description": setup_data.get("description", ""),
            "type": setup_data.get("type", ""),
            "dns_name": setup_data.get("dns_name", ""),
            "printer_ip": setup_data.get("printer_ip", ""),
            "model": setup_data.get("model", "")
        }
        
        for key, value in details_to_update.items():
            db_ref.child("details").child(key).set(value)
            
        logger.info(f"Printer {printer_name} setup completed successfully")
        
    except Exception as e:
        logger.error(f"Printer setup error: {e}")
        try:
            printer_ref.child("status").set(f"failed-{str(e)}")
            printer_ref.child("connection").set("failed")
        except Exception as update_error:
            logger.error(f"Could not update error status in Firebase: {update_error}")


def download_file(url, destination):
    """Download a file from the given URL to the destination path"""
    try:
        # This function would implement the actual download logic
        # You could use requests, urllib, or a custom method depending on the URL scheme
        logger.info(f"Downloading file from {url} to {destination}")
        
        # Example implementation (replace with actual logic):
        import requests
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            with open(destination, 'wb') as f:
                f.write(response.content)
            return True
        else:
            logger.error(f"Download failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return False





def main():
    """Main function to initialize and start listening for printer setup requests"""
    config = load_config()
    if not config:
        logger.error("Cannot proceed without configuration")
        return
        
    if not init_firebase():
        logger.error("Cannot proceed without Firebase")
        return
        
    try:
        # Listen for printer setup requests
        logger.info(f"Starting printer setup listener for printer code: {config['code']}")
        db.reference("/").child("Printers").child(config["code"]) \
          .child("printer_setup_process").child("start").listen(setup_printer)
    except Exception as e:
        logger.error(f"Listener setup failed: {e}")

if __name__ == "__main__":
    main()