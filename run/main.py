import os, logging, time, subprocess, socket, threading
import importlib.util
import json
import pexpect
import firebase_admin
from firebase_admin import credentials, db
import nmap
import requests

ENV_PATH = "/dev/shm/atomte_secrets.json"

def fetch_secrets():
    return {
        "type": "service_account",
        "project_id": "skilldevelopmentapp",
        "private_key_id": "8fe2d85fe1facb1cb538701ac9f9c287d847b4da",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC4tpp2cmJxDrg2\n7kMhci/24Sul78EW/5sphMG9WtUEvUmn4qhJu7JbFne10uPAZHrsPVqGob9A/pD6\nyLihb53vAJgZ+A+6wNVn8/iJU4GkWTpZbK+Ui50HJ8Etl5IzvaybRE3CnkGoQEeO\nDnruDCUAS3OhpcUmXGoP+vextZEnOkxqDdcDZEE6euBigviVbtsOobGmK2AM3SBy\nhJh4hIuslwovKkvV0d69L7L+sJ2vrqFDxpDC1cvLy7EyS22esq1rRlrrXc6WAcdY\nrtq9sVSn77Vx1hGcTYMXqlA465fsWs0DyDMEE1mFRjBpyj1uDFSPhxDEhpgJ6XJ9\n+gC0Yo29AgMBAAECgf9DQBpXFKiVgQo2fS6Zb7W7jscv18fXNd5tzmfocnx2cfvQ\nHJAKwMuvA+D7O3oZt6jNPAHBEchbf57f6+kuoV4ivN/vKx3aQogk3/JoZ43xfQOM\nx5Rw069Bp+TiJYHgrwhsrIg5xEaMxrxVqVlju3GfKdlgnz3khN8n1DBLTowKlfJB\ntJgHFyMXJblL/JPO73g2OGLvUa6FV2eYVxWFd/lYLnouGYA1mvWZhj1cVdGo6GSZ\nH5etutSymO4s8mdzAkIiBoCvJ1A8ArTpaVohGakfOCt4b9KuuEn4KFLBsIif5xwV\noa89496Kq8ZpnnU7MVATJ7fWBicFyF4+BCW4/kECgYEA6qNu6Fr0bPY8GbUhYam8\nK4UbVecKj+mh/D0MWQdgSVIjTexMsOVhYuEQSWakx7A1Wr+EebzD+DWhv9Qh7qEX\ndjc/a/ab3ZPSgV7C70KTYL4xyxz97h3V7dsi+xBITLQb5hNA91DErEx0xNsn/MUf\nfmiQw6V0beKIS+1aFdrAr+ECgYEAyYeY9gPcg42KqA1rTkt4kRTrOnEsh4zAEl5m\nd+KobqabUuWXzAOd0vIj5Imfart6bE5+Jz0/XKGrprO5jg8iCX6y3soUQ/TvX+Dg\nnNkeC4md7pN7KObhz0i2WikrBOI5p2YM6p6VYSaIAegHLrvRkpxEBHD3NwgiHgOn\nVFeryV0CgYEAvZH/qEDcHDCxDAAYkURGYE7xb+zzzqPvGNDl6gQYmgR/u5Q/vegF\nT5MQyozgcul9oez8BjMpjZ8fKNIl/BswznUCi6K5+UJWH+nEyvPaCJ6Bsl2hF0IJ\ntluHHprgHwChTbiek3IxBBfde7Ko0wMcV8/5reg+cg1FGzsPvnp3lWECgYEAkL7q\ntzBYzsf3ofJZcxez1gh/Vy94Ozd1sPvKfyr1rNvPTcAHwgmK7rrp2riaHo/fQzEx\nXL+Z5c9cuVP23zixSr6MfIYJ/jFLSML8sMsk0Eacf4HAAMWrxDTGfIV7F3vgywH6\nHv2d7vQ81ZmwpvlRcgr4s3Prq8QUtRgMtABwKyUCgYBJdVA+kcU4SzX01aU2ZnDj\nVClMbjZgqPNcYlxQmqbRLrq0SrX5NNiCI4F/AzHAPABs5/zCXRH6Lp5tBSDNYeUS\nRmP3OfaC+S3LDX0txmzniSBbuwUkNSByoRIimXQ2v082j7CmQ8TSqO5rQGolCCWv\n94CnapbQd4lRDi2bDo47xw==\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-tth3k@skilldevelopmentapp.iam.gserviceaccount.com",
        "client_id": "114268976436077987245",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-tth3k%40skilldevelopmentapp.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
def write_env_file(secrets):
    with open(ENV_PATH, "w") as f:
        json.dump(secrets, f, indent=4)
    os.chmod(ENV_PATH, 0o600)  # Restrict permissions
    
    #cred = credentials.Certificate(ENV_PATH)

# Setup logging
def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()

# Environment setup
def get_working_directory():
    os.chdir(os.getcwd() + "/Atomte/Atomte_raspberrypi")
    return os.getcwd() + "/run"

cwd = get_working_directory()
env = os.environ.copy()
env.update({
    "DISPLAY": ":0",
    "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
    "XDG_RUNTIME_DIR": "/run/user/1000"
})

# Load configuration
with open(cwd + "/../../secrets/details.json", "r") as f:
    config = json.load(f)

# Helper functions
def run_command(command, log_file):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT, env=env)
        process.communicate()

def run_subprocess(commands):
    try:
        logger.info(f"Running: {str(commands)}")
        result = subprocess.run(commands, cwd=cwd+"/", capture_output=True, text=True, env=env)
        logger.info(f"Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error running subprocess: {e}")
        return None

def run_web(command, project_dir):
    try:
        result = subprocess.run(command, cwd=cwd+project_dir, capture_output=True, text=True)
        logger.info(f"Running command: {' '.join(command)} in {cwd+project_dir}")
        logger.info(f"STDOUT: {result.stdout.strip()}")
        logger.warning(f"STDERR: {result.stderr.strip()}") if result.stderr else None
        logger.info(f"Return code: {result.returncode}")

        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Return code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Web command error: {e}")
        print(f"Web command error: {e}")
        return False

def update_firebase_serial_number():
    """Fetch and update the Raspberry Pi serial number in Firebase"""
    # Fetch serial number
    serial_number = None
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    serial_number = line.strip().split(':')[1].strip()
                    break
    except Exception as e:
        print("Error reading serial number:", e)
        return

    # Update Firebase
    if serial_number:
        db.reference('/').child("Printers").child(config["code"]).child("details").child("serial_no").set(serial_number)
        print("Serial number updated successfully in Firebase.")
    else:
        print("Failed to retrieve serial number.")

def wait_for_internet():
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            time.sleep(5)

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        db.reference('/').child("Printers").child(config["code"]).child("states").child("device_ip").set(True)
        return ip
    except Exception as e:
        logger.error(f"Error getting IP address: {e}")
        db.reference('/').child("Printers").child(config["code"]).child("states").child("device_ip").set(False)
        return None

def install_modules():
    run_subprocess(["../../venv/bin/python3", "../../venv/bin/pip3", "install", "-r", "../requirements.txt"])


def initialize_display():
    run_web(['sudo', 'npm', 'install', '-g', 'serve'], '/../atomte/')
    run_subprocess(["sudo", "cp", "../Atomte/boot_image/logo.png", "/usr/share/plymouth/themes/pix/splash.png"])
    run_subprocess(["chmod", "+x", cwd+"/orientation.sh"])
    run_subprocess(["chmod", "+x", cwd+"/../device_manager/launcher.sh"])
    run_subprocess(["sudo", "chmod", "+x", cwd+"/../device_manager/launcher.sh"])
    run_command("sudo "+cwd+"/orientation.sh", cwd+"/orientation.log")

def web_server_thread():
    run_web(['sudo', 'serve', '-s', 'build'], '/../atomte/')

def web_server_thread_for_users():
    run_web(['sudo', 'serve', '-s', 'build','-l','80'], '/../autoprint/')
    #pass

def write_json_file(file_path, data):
    """Write data to a JSON file"""
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        # Write JSON data with pretty formatting
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        logger.info(f"Successfully wrote data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write JSON file {file_path}: {e}")
        return False
    
# Main initialization
def first_time_setup():
    wait_for_internet()

    # Initialize Firebase
    cred = credentials.Certificate(cwd+"/../secrets/key.json")
    # cred = credentials.Certificate(ENV_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout': 10
    })
    update_firebase_serial_number()
    
    # Set initial configuration in Firebase
    db.reference('/').child("Printers").child(config["code"]).update({
        "details/password": config["password"],
        "details/type": "public",
        "details/id": config["code"],
        "setup": False,
        "lock1": False,
        "lock2": False,
        "power": True,
        "printer_setup": False,
        "select_properties": False,
        "updates": True,
        "audio": 50,
        "details/snmp":True,
        "mic": 50,
        "secrets": config,
        "details/pagecount": 0,
        "details/printed": 0,
    })
    install_modules()
    try:
        os.remove(cwd+"/../secrets/key.json")
    except Exception as e:
        logger.error("Error deleting file:", e)
    if config["type"] == "display":
        run_web(['npm', 'install'], '/../atomte/')
        run_web(['npm', 'run', 'build'], '/../atomte/')
    
    # Update local config
    config["setup"] = True
    with open(cwd+"/../../secrets/details.json", "w") as f:
        json.dump(config, f)
    
    # Display setup if needed
    if config["type"] == "display":
        initialize_display()
    
    run_subprocess(["sudo", "reboot"])

SERVER_URL = "https://atomte.com/api/get_firebase_token"

def get_cpu_serial():
    try:
        result = subprocess.run(
            ["cat", "/proc/cpuinfo"], capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Serial"):
                return line.split(":")[1].strip()
    except Exception as e:
        logger.error(f"Error fetching CPU serial: {e}")
    return None


def get_and_save_firebase_creds():
    serial = get_cpu_serial()
    if not serial:
        logger.error("Could not retrieve CPU serial.")
        return False

    payload = {
        "data": {
            "printer_id": config["code"],
            "serial_no": serial
        }
    }

    try:
        res = requests.post(SERVER_URL, json=payload, timeout=10)
        res.raise_for_status()
        response_data = res.json()

        if response_data.get("success") and response_data.get("data"):
            write_env_file(response_data["data"])
            logger.info("Firebase credentials saved successfully.")
            return True
        else:
            logger.error("Failed to retrieve credentials: %s", response_data.get("message"))
            return False

    except requests.RequestException as e:
        logger.error("HTTP request failed: %s", e)
        return False

# Main execution
if __name__ == "__main__":
    #for fetching and writing to ram
    # Start security check thread
    security_thread = threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 security/security_check.py", 
                                          "security/security_check.log"))
    security_thread.start()
    
    # Start WiFi setup thread
    wifi_thread = threading.Thread(target=run_command, 
                                 args=("sudo ../venv/bin/python3 setup_wifi/main.py", 
                                      "setup_wifi/main.log"))
    wifi_thread.start()
    
    # First time setup or regular startup
    if not config["setup"]:
        first_time_setup()
    else:
        # Wait for internet connection
        wait_for_internet()
        
        get_and_save_firebase_creds()

        # Initialize Firebase
        #cred = credentials.Certificate(cwd+"/../secrets/key.json")
        cred = credentials.Certificate(ENV_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
            'httpTimeout': 10
        })
        
        # Set internet connection status
        while 1:
            try:
                db.reference('/').child("Printers").child(config["code"]).child("states").child("internet").set(True)
                break
            except Exception as e:
                logger.error(f"Internet connection error. Retrying... {e}")
                time.sleep(3)
        
        # Update IP address
        db.reference('/').child("Printers").child(config["code"]).child("details").child("device_ip").set(get_ip_address())
        
        # Check for updates
        if config.get("updates", False):
            # pull_repository()
            install_modules()
            
            if config["type"] == "display":
                run_web(['npm', 'install'], '/../atomte/')
                run_web(['npm', 'run', 'build'], '/../atomte/')
                
            db.reference('/').child("Printers").child(config["code"]).child("updates").set(False)
            run_subprocess(["sudo", "reboot"])
            config["updates"] = False
            write_json_file(cwd+"/../../secrets/details.json", config)
         
        # Start web interface if needed
        if config["type"] == "display":
            web_thread = threading.Thread(target=web_server_thread)
            web_thread.start()
            
        # Start core services
        threads = []
        
        # Web interface
        threads.append(threading.Thread(target=run_command, 
                                     args=("../venv/bin/python3 run/startweb.py", 
                                          "run/startweb.log")))
        
        # System services
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 heart_beat/main.py", 
                                          "heart_beat/main.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 terminal/terminal.py", 
                                          "terminal/terminal.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 setup_printer/main.py", 
                                          "setup_printer/main.log")))
        
        # Get printer IP from database
        printer_ip = db.reference('/').child("Printers").child(config["code"]).child("details").child("ip").get()
        
        # Start printer-related services if printer is configured
        if printer_ip and printer_ip != "":
            db.reference('/').child("Printers").child(config["code"]).child("states").child("printer_connection").set(True)
            
            if db.reference('/').child("Printers").child(config["code"]).child("details").child("type").get() == "public":
                threads.append(threading.Thread(target=run_command, 
                                             args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_public.py", 
                                                  "printer_manager/prints_manager_for_public.log")))
            else:
                web_thread_for_users = threading.Thread(target=web_server_thread_for_users)
                web_thread_for_users.start()

                threads.append(threading.Thread(target=run_command, 
                                             args=("sudo ../venv/bin/python3 qr_manager/qr_scanner.py", 
                                                  "qr_manager/qr_scanner.log")))
                
                threads.append(threading.Thread(target=run_command, 
                                             args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_private.py", 
                                                  "printer_manager/prints_manager_for_private.log")))
                
                threads.append(threading.Thread(target=run_command, 
                                             args=("sudo ../venv/bin/python3 printer_manager/files_from_server.py", 
                                                  "printer_manager/files_from_server.log")))
        else:
            db.reference('/').child("Printers").child(config["code"]).child("states").child("printer_connection").set(False)
        
        # Start additional services
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 device_manager/restart_device.py", 
                                          "device_manager/restart_device.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 device_manager/updates_checker.py", 
                                          "device_manager/updates_checker.log")))

        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 ads_manager/main.py", 
                                          "ads_manager/main.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 ads_manager/files_server.py", 
                                          "ads_manager/files_server.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 ads_manager/listner.py", 
                                          "ads_manager/listner.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 paper_manager/main1.py", 
                                          "paper_manager/main1.log")))
        
        threads.append(threading.Thread(target=run_command, 
                                     args=("sudo ../venv/bin/python3 device_manager/devicecontrol.py", 
                                          "device_manager/devicecontrol.log"), 
                                     daemon=True))
        
        
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for core services to complete
        for thread in threads[:3]:
            thread.join()