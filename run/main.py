import os, logging, time, subprocess, socket, threading
import importlib.util
import json
import pexpect
import firebase_admin
from firebase_admin import credentials, db
import nmap

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
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        print(f"Return code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"Web command error: {e}")
        return False

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

def setup_ssh():
    try:
        result = subprocess.run(['ssh-agent', '-s'], capture_output=True, text=True, check=True)
        output = result.stdout
        logger.info(f"SSH Agent started: {output}")
        
        for line in output.splitlines():
            if line.startswith('SSH_AUTH_SOCK'):
                os.environ['SSH_AUTH_SOCK'] = line.split(';')[0].split('=')[1]
            if line.startswith('SSH_AGENT_PID'):
                os.environ['SSH_AGENT_PID'] = line.split(';')[0].split('=')[1]
                
        run_subprocess(["chmod", "600", cwd+"/../ssh_key"])
        add_ssh_key("8985")
    except Exception as e:
        logger.error(f"SSH setup error: {e}")

def add_ssh_key(passphrase):
    try:
        if 'SSH_AUTH_SOCK' not in os.environ:
            raise Exception("SSH agent not running")
        
        child = pexpect.spawn(f'ssh-add {cwd}/../ssh_key')
        child.expect('Enter passphrase', timeout=5)
        child.sendline(passphrase)
        child.expect(pexpect.EOF)
        logger.info("SSH key added successfully")
        return True
    except Exception as e:
        logger.error(f"SSH key error: {e}")
        return False
def pull_repository():
    setup_ssh()
    run_subprocess(["sudo", "chown", "-R", f"atomte{config['code']}:atomte{config['code']}", ".git"])
    run_subprocess(["git", "fetch", "origin", "master"])
    try:
        result = run_subprocess(["git", "pull", "--rebase", "origin", "master"])
        logger.info("✅ Git pull completed successfully.")
    except subprocess.CalledProcessError:
        run_subprocess(["git", "rebase", "--abort"])
        logger.error("⚠️ Git rebase failed due to conflict. Rebase aborted.")
        result = None
    return result


def initialize_display():
    run_web(['sudo', 'npm', 'install', '-g', 'serve'], '/../atomte/')
    run_subprocess(["sudo", "cp", "../Atomte/boot_image/logo.png", "/usr/share/plymouth/themes/pix/splash.png"])
    run_subprocess(["chmod", "+x", cwd+"/orientation.sh"])
    run_subprocess(["chmod", "+x", cwd+"/../device_manager/launcher.sh"])
    run_subprocess(["sudo", "chmod", "+x", cwd+"/../device_manager/launcher.sh"])
    run_command("sudo "+cwd+"/orientation.sh", cwd+"/orientation.log")

def web_server_thread():
    run_web(['sudo', 'serve', '-s', 'build'], '/../atomte/')

# Main initialization
def first_time_setup():
    wait_for_internet()
    # Initialize Firebase
    cred = credentials.Certificate(cwd+"/../secrets/key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout': 10
    })
    
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
        "mic": 50,
        "secrets": config
    })
    
    # Update local config
    config["setup"] = True
    with open(cwd+"/../../secrets/details.json", "w") as f:
        json.dump(config, f)
    
    # Display setup if needed
    if config["type"] == "display":
        initialize_display()
    
    run_subprocess(["sudo", "reboot"])

# Main execution
if __name__ == "__main__":
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
        
        # Initialize Firebase
        cred = credentials.Certificate(cwd+"/../secrets/key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
            'httpTimeout': 10
        })
        
        # Set internet connection status
        db.reference('/').child("Printers").child(config["code"]).child("states").child("internet").set(True)
        
        # Update IP address
        db.reference('/').child("Printers").child(config["code"]).child("details").child("device_ip").set(get_ip_address())
        
        # Check for updates
        if db.reference('/').child("Printers").child(config["code"]).child("updates").get():
            pull_repository()
            install_modules()
            
            if config["type"] == "display":
                run_web(['npm', 'install'], '/../atomte/')
                run_web(['npm', 'run', 'build'], '/../atomte/')
                
            db.reference('/').child("Printers").child(config["code"]).child("updates").set(False)
            run_subprocess(["sudo", "reboot"])
         
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
                                     args=("sudo ../venv/bin/python3 ads_manager/main.py", 
                                          "ads_manager/main.log")))
        
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