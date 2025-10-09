import os, logging, time, subprocess, socket, threading
import importlib.util
import json
import pexpect
import firebase_admin
from firebase_admin import credentials, db
import nmap
import requests

ENV_PATH = "/dev/shm/atomte_secrets.json"


    
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
def run_command(command, log_file,cwd=None):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=cwd)
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
    run_web(['sudo','npm','run','electron'], '/../atomte/')

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
        "load_data": True,
        "details/pagecount": 0,
        "details/printed": 0,
        "videos":{"ad1":"https://firebasestorage.googleapis.com/v0/b/skilldevelopmentapp.appspot.com/o/videos%2FWhatsApp%20Video%202025-05-12%20at%2016.10.13.mp4?alt=media&token=2149da0e-1b8d-49a6-93fa-4ad165bcb093", 
                  "ad2":"https://firebasestorage.googleapis.com/v0/b/skilldevelopmentapp.appspot.com/o/videos%2Fad1.mp4?alt=media&token=5d800f0d-d892-437c-b0be-f2c2cdc31b9b", 
                  "ad3":"https://firebasestorage.googleapis.com/v0/b/skilldevelopmentapp.appspot.com/o/videos%2FTom%20%26%20Jerry%20(1940)%20-%20E16%20-%20Puttin'%20On%20The%20Dog%20.mp4?alt=media&token=672411b5-2d87-4f7e-804e-826ec16516d2"},
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
                
            db.reference('/').child("Printers").child(config["code"]).child("updated").set(True)
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
        threads.append(threading.Thread(
            target=run_command,
            args=("npm run electron -- --no-sandbox", "run/startweb.log", cwd+"/../atomte/")
        ))
        
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
                try:
                    if(db.reference('autoprintonline').child("active_printer").get() != config["code"]):
                        threads.append(threading.Thread(target=run_command, 
                                                    args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_public.py", 
                                                        "printer_manager/prints_manager_for_public.log")))
                    else:
                        threads.append(threading.Thread(target=run_command, 
                                                    args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_online.py", 
                                                        "printer_manager/prints_manager_for_online.log")))
                except Exception as e:
                    logger.error(f"Error checking active printer: {e}")
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