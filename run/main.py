import os,logging,time,subprocess,socket,threading
import importlib.util
import nmap

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

env = os.environ.copy()
env["DISPLAY"] = ":0"
env["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
env["XDG_RUNTIME_DIR"] = "/run/user/1000"


def run_command(command, log_file):
    with open(log_file, 'a') as log:
        log.write(f"\n=== Reboot Triggered at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        process = subprocess.Popen(command, shell=True, stdout=log, stderr=subprocess.STDOUT,env=env)
        process.communicate()



def run_subprocess(commands):
    try:
        logger.info(f"running: {str(commands)}..")
        result = subprocess.run(commands, 
                                cwd=cwd+"/",
                                capture_output=True, 
                                text=True,
                                env=env)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"An error occurred during git pull: {e}")
import json
with open(cwd+"/../../secrets/details.json", "r") as f:
    data = json.load(f)


security_check = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 security/security_check.py","security/security_check.log"))
security_check.start()
t1 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 setup_wifi/main.py","setup_wifi/main.log"))
t1.start()


def run_web(command, project_dir):
    try:
        result = subprocess.run(command, cwd=cwd+project_dir, capture_output=True, text=True)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        print("Return code:", result.returncode)
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def init_setup():
    offline_time = 0  # Track how long the internet is down
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            offline_time = 0  # Reset counter when internet is available
            break
        except OSError: 
            offline_time += 5  # Increase the offline counter
            if offline_time >= 120:  # If no internet for 2 mins
                run_subprocess(["sudo", "reboot"])
                time.sleep(5)  # Prevent immediate loop execution
        time.sleep(5)
    run_subprocess(["../../venv/bin/python3","../../venv/bin/pip3", "install", "-r", "../requirements.txt"])
def is_module_installed(module_name):
    spec = importlib.util.find_spec(module_name)
    return spec is not None
if(data["setup"] == False):
    init_setup()
    if(not is_module_installed("firebase_admin")):
        run_subprocess(["sudo","reboot"])
    import firebase_admin
    from firebase_admin import credentials, db
    cred = credentials.Certificate(cwd+"/../secrets/key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout':10
    })
    if(data["type"] == "display"):
        run_web(['sudo','npm', 'install','-g', 'serve'], '/../atomte/')
    db.reference('/').child("Printers").child(data["code"]).child("details").child("password").set(data["password"])
    db.reference('/').child("Printers").child(data["code"]).child("details").child("type").set("public")
    db.reference('/').child("Printers").child(data["code"]).child("details").child("id").set(data["code"])
    db.reference('/').child("Printers").child(data["code"]).child("setup").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("lock1").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("lock2").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("power").set(True)
    db.reference('/').child("Printers").child(data["code"]).child("printer_setup").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("select_properties").set(False)
    db.reference('/').child("Printers").child(data["code"]).child("updates").set(True)
    db.reference('/').child("Printers").child(data["code"]).child("audio").set(50)
    db.reference('/').child("Printers").child(data["code"]).child("mic").set(50)
    db.reference('/').child("Printers").child(data["code"]).child("secrets").set(data)
    with open(cwd+"/../../secrets/details.json", "w") as f:
        data["setup"] = True
        json.dump(data, f)
    if(data["type"] == "display"):
        run_subprocess(["sudo", "cp", "../Atomte/boot_image/logo.png","/usr/share/plymouth/themes/pix/splash.png"])
        run_subprocess(["chmod","+x",cwd+"/orientation.sh"])
        run_subprocess(["chmod","+x",cwd+"/../device_manager/launcher.sh"])
        run_subprocess(["sudo","chmod","+x",cwd+"/../device_manager/launcher.sh"])
        run_command("sudo "+cwd+"/orientation.sh", cwd+"/orientation.log")
    
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


while 1:
    try:
        db.reference('/').child("Printers").child(data["code"]).child("states").child("internet").set(True)
        break
    except Exception as e:
        logger.error(f"Error checking internet connection: {e}")
        time.sleep(1)
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

def run_web_tread():
    run_web(['sudo','serve','-s','build'],'/../atomte/')
if(data["type"] == "display"):
    web_t = threading.Thread(target=run_web_tread)
    web_t.start()
    time.sleep(1)
# web_command={
#         "command": cwd + "/start_website.sh",
#         "log_file": cwd + "/start_website.log"
#     }
# if(data["type"] == "display"):
#     t_r = threading.Thread(target=run_command, args=(web_command['command'], web_command['log_file']))
#     t_r.start()



def pull_repo():
    start_ssh_agent()
    run_subprocess(["chmod","600",cwd+"/../ssh_key"])
    add_ssh_key_with_passphrase(cwd+"/../ssh_key", "8985")
    run_subprocess(["git","stash"])
    # run_subprocess(["git", "pull", "--rebase", "origin", "master"])
    subprocess.run(["git", "pull", "--rebase", "origin", "master"], 
                        cwd=cwd+"/",
                        capture_output=True, 
                        text=True)
if(db.reference('/').child("Printers").child(data["code"]).child("updates").get()):
    pull_repo()
    install_modules()
    if(data["type"] == "display"):
        run_web(['npm', 'install'],'/../atomte/')
        run_web(['npm','run','build'],'/../atomte/')
    db.reference('/').child("Printers").child(data["code"]).child("updates").set(False)
    run_subprocess(["sudo","reboot"])

# os.system(f"{cwd}/../../venv/bin/python {cwd}/startweb.py >> {cwd}/startweb.log 2>&1")
# with open(f"{cwd}/startweb.log", "a") as log_file:
#     subprocess.run([f"{cwd}/../../venv/bin/python", f"{cwd}/startweb.py"], 
#                cwd=cwd+"/",
#                capture_output=True, 
#                text=True,env=env)


w_t = threading.Thread(target=run_command, args=("../venv/bin/python3 run/startweb.py","run/startweb.log"))
w_t.start()


t2 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 heart_beat/main.py","heart_beat/main.log"))
t2.start()



t3 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 setup_printer/main.py","setup_printer/main.log"))
t3.start()




printer_ip=db.reference('/').child("Printers").child(data["code"]).child("details").child("ip").get()
def get_ip():
    nm = nmap.PortScanner()
    nm.scan(hosts='192.168.2.0/24', arguments='-sn --host-timeout .2s')
    hosts_up = nm.all_hosts()
    for host in hosts_up:
        if(host!="192.168.2.1"):	
            print(host)
            return host
    return None

# ip_address=get_ip()
# if(ip_address!=None):
#     db.reference('/').child("Printers").child(data["code"]).child("states").child("printer_connection").set(True)
#     db.reference('/').child("Printers").child(data["code"]).child("details").child("ip").set(ip_address)
if(printer_ip!=None and printer_ip!=""):
    if(db.reference('/').child("Printers").child(data["code"]).child("details").child("type").get()=="public"):
        t6 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_public.py","printer_manager/prints_manager_for_public.log"))
        t6.start()
    else:
        t5 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 qr_manager/qr_scanner.py","qr_manager/qr_scanner.log"))
        t5.start()
        t6 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 printer_manager/prints_manager_for_private.py","printer_manager/prints_manager_for_private.log"))
        t6.start()
        t4 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 printer_manager/files_from_server.py","printer_manager/files_from_server.log"))
        t4.start()
else:
    db.reference('/').child("Printers").child(data["code"]).child("states").child("printer_connection").set(False)
t7 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 device_manager/restart_device.py","device_manager/restart_device.log"))
t7.start()
t8 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 ads_manager/main.py","ads_manager/main.log"))
t8.start()
t9 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 paper_manager/main1.py","paper_manager/main1.log"))
t9.start()
t10 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 device_manager/devicecontrol.py","device_manager/devicecontrol.log"),daemon=True)
t10.start()
t11 = threading.Thread(target=run_command, args=("sudo ../venv/bin/python3 run/playvideo.py","run/playvideo.log"))
t11.start()
# os.system("/home/atomte100016/Atomte/Atomte_raspberrypi/../venv/bin/python /home/atomte100016/Atomte/Atomte_raspberrypi/device_manager/devicecontrol.py")

threads=[]
threads.append(t1)
threads.append(t2)
threads.append(t3)

threads.append(t7)
threads.append(t8)
threads.append(t9)
# threads.append(t10)
for thread in threads:
    thread.join()