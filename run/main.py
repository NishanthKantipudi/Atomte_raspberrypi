import os,logging,time,subprocess,socket,threading

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()

def getcwd():
    cwd = os.getcwd()
    os.chdir(cwd+"/Atomte/Atomte_raspberrypi")
    cwd = os.getcwd()+"/run"
    return cwd
cwd=getcwd()


def run_command(command, log_file):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Reboot Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT)
        process.communicate()

def run_subprocess(commands):
    try:
        logger.info(f"running: {str(commands)}...")
        result = subprocess.run(commands, 
                                cwd=cwd+"/",
                                capture_output=True, 
                                text=True)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"An error occurred during git pull: {e}")
import json
with open(cwd+"/../../secrets/details.json", "r") as f:
    data = json.load(f)

t1 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 setup_wifi/main.py","setup_wifi/main.log"))
t1.start()





def init_setup():
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            break
        except OSError: 
            time.sleep(1)
    run_subprocess(["../../venv/bin/python3","../../venv/bin/pip3", "install", "-r", "../requirements.txt"])

if(data["setup"] == False):
    init_setup()
    import firebase_admin
    from firebase_admin import credentials, db
    cred = credentials.Certificate(cwd+"/../secrets/key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout':10
    })
    db.reference('/').child("Printers").child(data["code"]).child("details").child("password").set(data["password"])
    db.reference('/').child("Printers").child(data["code"]).child("setup").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("printer_setup").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("select_properties").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("updates").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("secrets").set(data)
    with open(cwd+"/../../secrets/details.json", "w") as f:
        data["setup"] = True
        json.dump(data, f)
else:
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            break
        except OSError: 
            time.sleep(1)
    import firebase_admin
    from firebase_admin import credentials, db
    cred = credentials.Certificate(cwd+"/../secrets/key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout':10
    })
db.reference('/').child("Printers").child(data["code"]).child("states").child("internet").set(True)
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        db.reference('/').child("Printers").child(data["code"]).child("states").child("device_ip").set(True)
        return s.getsockname()[0]
    except Exception as e:
        logger.error(f"Error getting IP address: {e}")
        db.reference('/').child("Printers").child(data["code"]).child("states").child("device_ip").set(False)
        return None


db.reference('/').child("Printers").child(data["code"]).child("details").child("device_ip").set(get_ip_address())

def start_ssh_agent():
    try:
        result = subprocess.run(['ssh-agent', '-s'], capture_output=True, text=True, check=True)
        output = result.stdout
        logger.info(f"SSH Agent started successfully: {output}")
        for line in output.splitlines():
            if line.startswith('SSH_AUTH_SOCK'):
                ssh_auth_sock = line.split(';')[0].split('=')[1]
                os.environ['SSH_AUTH_SOCK'] = ssh_auth_sock
            if line.startswith('SSH_AGENT_PID'):
                ssh_agent_pid = line.split(';')[0].split('=')[1]
                os.environ['SSH_AGENT_PID'] = ssh_agent_pid
    except Exception as e:
        logger.error(f"Error starting SSH Agent: {e}")
        print(f"Error starting SSH Agent: {e}")
def add_ssh_key_with_passphrase(keyfile, passphrase):
    try:
        if 'SSH_AUTH_SOCK' not in os.environ:
            raise Exception("SSH agent is not running. Cannot add SSH key.")
        child = pexpect.spawn(f'ssh-add {keyfile}')
        child.expect('Enter passphrase', timeout=5)
        child.sendline(passphrase)
        child.expect(pexpect.EOF)
        logger.info("SSH key added successfully.")
        return True
    except pexpect.exceptions.EOF as e:
        logger.error(f"EOF error while adding SSH key: {e}")
        return False
    except pexpect.exceptions.TIMEOUT as e:
        logger.error(f"Timeout error while adding SSH key: {e}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while adding SSH key: {e}")
        return False


def install_modules():
    run_subprocess(["../../venv/bin/python3","../../venv/bin/pip3", "install", "-r", "../requirements.txt"])


import pexpect

def pull_repo():
    start_ssh_agent()
    run_subprocess(["chmod","600",cwd+"/../ssh_key"])
    add_ssh_key_with_passphrase(cwd+"/../ssh_key", "8985")
    run_subprocess(["git", "pull","origin", "master"])
if(db.reference('/').child("Printers").child(data["code"]).child("updates").get()):
    pull_repo()
    install_modules()
    db.reference('/').child("Printers").child(data["code"]).child("updates").set(False)


t2 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 heart_beat/main.py","heart_beat/main.log"))
t2.start()


t3 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 setup_printer/main.py","setup_printer/main.log"))
t3.start()


t4 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 printer_manager/files_from_server.py","printer_manager/files_from_server.log"))
t4.start()


t5 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 qr_manager/qr_scanner.py","qr_manager/qr_scanner.log"))
t5.start()


if(db.reference('/').child("Printers").child(data["code"]).child("details").child("type").get()=="public"):
    t6 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_public.py","printer_manager/prints_manager_for_public.log"))
    t6.start()
else:
    t6 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_private.py","printer_manager/prints_manager_for_private.log"))
    t6.start()

t7 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 device_manager/restart_device.py","device_manager/restart_device.log"))
t7.start()