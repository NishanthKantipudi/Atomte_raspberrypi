import subprocess
import threading
import queue
import time
import traceback
import json
import os
import logging
import firebase_admin
from firebase_admin import credentials, db

def setup_logger():
    """Configure and return a logger with more robust logging."""
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('printer_setup.log'),  # Log to file
            logging.StreamHandler()  # Also log to console
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

def load_configuration():
    """
    Safely load configuration files with error handling.
    Returns a tuple of (current working directory, secrets data)
    """
    try:
        cwd = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(cwd,"..", "secrets", "key.json")
        details_path = os.path.join(cwd,"..", "..", "secrets", "details.json")
        
        if not os.path.exists(key_path):
            logger.error(f"Firebase credentials file not found: {key_path}")
            return None, None
        
        if not os.path.exists(details_path):
            logger.error(f"Details file not found: {details_path}")
            return None, None
        
        # Load credentials and details
        cred = credentials.Certificate(key_path)
        with open(details_path, "r") as f:
            s_data = json.load(f)
        
        return cwd, s_data
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None, None

def initialize_firebase(cred, database_url):
    """
    Initialize Firebase with robust error handling
    """
    try:
        firebase_admin.initialize_app(cred, {
            'databaseURL': database_url,
            'storageBucket': 'skilldevelopmentapp.appspot.com'
        })
        logger.info("Firebase initialized successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        raise

def run_command_with_timeout(command, timeout=30):
    """
    Enhanced command execution with better error handling and logging
    """
    output_queue = queue.Queue()
    error_queue = queue.Queue()
    
    def target():
        try:
            logger.info(f"Executing command: {' '.join(command)}")
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()
            output_queue.put(stdout)
            error_queue.put(stderr)
            output_queue.put(process.returncode)
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            error_queue.put(str(e))
            output_queue.put(None)
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    
    thread.join(timeout)
    
    if thread.is_alive():
        logger.warning(f"Command timed out after {timeout} seconds")
        return (None, None, f"Command timed out after {timeout} seconds")
    
    try:
        return_code = output_queue.get(block=False)
        stdout = output_queue.get(block=False)
        stderr = error_queue.get(block=False)
        
        if return_code != 0:
            logger.error(f"Command failed with return code {return_code}")
            logger.error(f"Stderr: {stderr}")
        
        return (return_code, stdout, stderr)
    except queue.Empty:
        logger.error("Failed to retrieve command output")
        return (None, None, "Failed to retrieve command output")

def get_printer_properties(printer_name, timeout=10):
    """
    Retrieve and parse printer properties with enhanced error handling
    """
    try:
        command = ["lpoptions", "-p", printer_name, "-l"]
        return_code, stdout, stderr = run_command_with_timeout(command, timeout)
        logger.info(f"{return_code}, {stdout}, {stderr}")
        if stdout is None or stdout != 0:
            logger.error(f"Failed to get properties for printer '{printer_name}': {stderr}")
            return None
        
        properties = {}
        for line in return_code.strip().split("\n"):
            if ":" in line:
                line_parts = line.split(":")
                option_name = line_parts[0].replace("/", ":")
                choices = line_parts[1].split()
                
                if len(choices) > 1:
                    properties[option_name] = [
                        {"name": choice, "cost": 0.0} 
                        for choice in choices
                        if choice
                    ]
        
        if not properties:
            logger.warning("No printer properties retrieved")
            return None
        
        logger.info(f"Printer Properties: {properties}")
        return properties
    
    except Exception as e:
        logger.error(f"Unexpected error retrieving printer properties: {e}")
        traceback.print_exc()
        return None

def setup(snap):
    """
    Enhanced printer setup with comprehensive error handling and logging
    """
    if not snap.data:
        logger.warning("No printer setup data provided.")
        return
    try:
        printer_ref = db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process")
        
        if printer_ref.child("start").get():
            printer_ref.child("start").set(False)
            data = printer_ref.get()
            # Validate required printer setup data
            required_keys = ['name', 'printer_ip']
            if not all(key in data for key in required_keys):
                logger.error("Missing required printer setup data")
                printer_ref.child("status").set("failed-missing_data")
                return
            command = [
                "lpadmin", 
                "-p", db.reference("/").child("Printers").child(s_data["code"]).child("details").child("name").get(), 
                "-E", 
                "-v", f"ipp://{data['printer_ip']}/ipp/print", 
                "-m", "lsb/usr/cupsfilters/Generic-PDF_Printer-PDF.ppd"
            ]
            return_code, stdout, stderr = run_command_with_timeout(command, timeout=15)
            printer_ref.child("status").set("connecting")
            logger.info(f"{return_code}, {stdout}, {stderr}")
            if stdout == 0:
                logger.info("Printer added successfully!")
                
                try:
                    props = get_printer_properties(data["name"])

                    props={
                        "paper_size": [
        {"name": "a4", "cost": 0,"value":0,"pc":1},
        {"name": "letter", "cost": 0,"value":0,"pc":1},
        {"name": "legal", "cost": 0,"value":0,"pc":1},
        {"name": "a3", "cost": 0,"value":1,"pc":1},
        {"name": "custom_size", "cost": 0,"value":0,"pc":1}
    ],
    "orientation": [
        {"name": "portrait", "cost": 0,"value":0,"pc":1},
        {"name": "landscape", "cost": 0,"value":0,"pc":1},
        {"name": "reverse_portrait", "cost": 0,"value":0,"pc":1},
        {"name": "reverse_landscape", "cost": 0,"value":0,"pc":1}
    ],
    "print_quality": [
        {"name": "draft", "cost": 0,"value":1,"pc":1},
        {"name": "normal", "cost": 0,"value":2,"pc":1},
        {"name": "high", "cost": 0,"value":3,"pc":1},
        {"name": "photo", "cost": 0,"value":4,"pc":1}
    ],
    "color_mode": [
        {"name": "color", "cost": 0,"value":2,"pc":1},
        {"name": "grayscale", "cost": 0,"value":0,"pc":1},
        {"name": "black_and_white", "cost": 0,"value":0,"pc":1}
    ],
    "duplex_printing": [
        {"name": "one_sided", "cost": 0,"value":1.5,"pc":1},
        {"name": "two_sided_long_edge", "cost": 2,"value":2,"pc":0.5},
        {"name": "two_sided_short_edge", "cost": 0,"value":2,"pc":0.5}
    ],
    "paper_source": [
        {"name": "main_tray", "cost": 0,"value":0,"pc":1},
        {"name": "manual_feed", "cost": 0,"value":0,"pc":1},
        {"name": "alternative_tray", "cost": 0,"value":0,"pc":1}
    ],
    "stapling": [
        {"name": "no_staple", "cost": 0,"value":0,"pc":1},
        {"name": "top_left", "cost": 1,"value":0,"pc":1},
        {"name": "top_right", "cost": 1,"value":0,"pc":1},
        {"name": "bottom_left", "cost": 1,"value":0,"pc":1},
        {"name": "bottom_right", "cost": 1,"value":0,"pc":1}
    ],
    "paper_type": [
        {"name": "plain", "cost": 0,"value":0,"pc":1},
        {"name": "recycled", "cost": 0,"value":0,"pc":1},
        {"name": "glossy", "cost": 0.5,"value":0,"pc":1},
        {"name": "transparency", "cost": 0.5,"value":0,"pc":1},
        {"name": "labels", "cost": 1,"value":0,"pc":1}
    ]
                    }

                    if props is not None:
                        printer_ref.child("properties").set(props)
                        printer_ref.child("connection").set("success")
                        time.sleep(2)
                        db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup").set(True)
                    else:
                        logger.warning("Failed to retrieve printer properties")
                        printer_ref.child("status").set("failed-no_properties")
                        printer_ref.child("connection").set("failed")
                
                except Exception as prop_error:
                    logger.error(f"Error retrieving printer properties: {prop_error}")
                    printer_ref.child("status").set(f"failed-{str(prop_error)}")
                    printer_ref.child("connection").set("failed")
            
            else:
                logger.error(f"Printer addition failed. Stderr: {stderr}")
                printer_ref.child("status").set(f"failed-{stderr}")
                printer_ref.child("connection").set("failed")
        
        else:
            logger.warning("No active printer setup process found.")
            printer_ref.child("status").set("failed")
    
    except Exception as e:
        logger.error(f"Unexpected error in printer setup: {e}")
        traceback.print_exc()
        
        try:
            printer_ref.child("status").set(f"failed-{str(e)}")
            printer_ref.child("connection").set("failed")
        except Exception as network_error:
            logger.error(f"Network error setting printer setup status: {network_error}")

# Configuration and initialization
cwd, s_data = load_configuration()
if cwd and s_data:
    try:
        initialize_firebase(
            credentials.Certificate(os.path.join(cwd, "..","secrets", "key.json")), 
            'https://skilldevelopmentapp-default-rtdb.firebaseio.com/'
        )
        db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("start").listen(setup)
    except Exception as init_error:
        logger.error(f"Initialization failed: {init_error}")
else:
    logger.error("Failed to load configuration. Exiting.")