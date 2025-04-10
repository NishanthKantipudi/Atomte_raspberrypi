import os
import subprocess
import pexpect
import logging
import json
import time
import firebase_admin
from firebase_admin import credentials, db

# Setup paths
cwd = os.getcwd()
CONFIG_PATH = os.path.join(cwd, "../secrets/details.json")
CRED_PATH = os.path.join(cwd, "secrets/key.json")
SSH_KEY_PATH = os.path.join(cwd, "ssh_key")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_json_file(file_path):
    """Load and parse a JSON file"""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Failed to read JSON file {file_path}: {e}")
        raise
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
def run_subprocess(command, capture_output=True, check=True, shell=False, text=True):
    """Run a subprocess command and log results"""
    cmd_str = command if isinstance(command, str) else " ".join(command)
    logger.info(f"Running: {cmd_str}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=text,
            check=check,
            shell=shell
        )
        logger.info(f"Result: {result}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise

def add_github_to_known_hosts():
    """Add GitHub's host key to known_hosts file"""
    try:
        # Ensure .ssh directory exists
        ssh_dir = os.path.expanduser("~/.ssh")
        os.makedirs(ssh_dir, exist_ok=True)
        
        # Check if known_hosts file exists, create if not
        known_hosts_file = os.path.join(ssh_dir, "known_hosts")
        if not os.path.exists(known_hosts_file):
            open(known_hosts_file, 'a').close()
            os.chmod(known_hosts_file, 0o600)
        
        # Add GitHub's host key using ssh-keyscan
        logger.info("Adding GitHub to known_hosts...")
        result = run_subprocess(["ssh-keyscan", "-t", "rsa", "github.com"])
        
        if result.returncode == 0:
            with open(known_hosts_file, 'a') as f:
                f.write(result.stdout)
            logger.info("GitHub host key added to known_hosts")
            return True
        else:
            logger.error("Failed to get GitHub host key")
            return False
    except Exception as e:
        logger.error(f"Error adding GitHub to known_hosts: {e}")
        return False

def setup_ssh():
    """Configure SSH agent and add SSH key"""
    try:
        result = run_subprocess(['ssh-agent', '-s'])
        output = result.stdout
        
        # Extract SSH environment variables
        for line in output.splitlines():
            if line.startswith('SSH_AUTH_SOCK'):
                os.environ['SSH_AUTH_SOCK'] = line.split(';')[0].split('=')[1]
            if line.startswith('SSH_AGENT_PID'):
                os.environ['SSH_AGENT_PID'] = line.split(';')[0].split('=')[1]
        
        # Set proper permissions on SSH key
        run_subprocess(["chmod", "600", SSH_KEY_PATH])
        
        # Add GitHub to known_hosts
        if not add_github_to_known_hosts():
            logger.warning("Failed to add GitHub to known_hosts. Host verification might fail.")
        
        # Add SSH key
        return add_ssh_key("8985")
    except Exception as e:
        logger.error(f"SSH setup error: {e}")
        return False

def add_ssh_key(passphrase):
    """Add SSH key to the SSH agent"""
    try:
        if 'SSH_AUTH_SOCK' not in os.environ:
            raise Exception("SSH agent not running")
        
        child = pexpect.spawn(f'ssh-add {SSH_KEY_PATH}')
        child.expect('Enter passphrase', timeout=5)
        child.sendline(passphrase)
        child.expect(pexpect.EOF)
        logger.info("SSH key added successfully")
        return True
    except Exception as e:
        logger.error(f"SSH key error: {e}")
        return False

def pull_repository():
    """Pull the latest changes from the git repository"""
    config = read_json_file(CONFIG_PATH)
    if not setup_ssh():
        logger.error("SSH setup failed, cannot pull repository")
        return False
    
    repo_dir = cwd
    os.chdir(repo_dir)
    
    try:      
        # Configure repository as safe directory if needed
        try:
            run_subprocess(["git", "pull", "--rebase", "origin", "master"])
        except subprocess.CalledProcessError as e:
            if "dubious ownership" in e.stderr:
                logger.info("Dubious ownership detected. Configuring safe.directory.")
                run_subprocess(["git", "config", "--global", "--add", "safe.directory", "*"])
                run_subprocess(["git", "pull", "origin", "master"])
            else:
                # If it's another error, handle it
                if "rebase" in e.stderr:
                    logger.warning("Git rebase failed. Aborting rebase.")
                    run_subprocess(["git", "rebase", "--abort"])
                raise
        
        logger.info("✅ Git pull completed successfully.")
        config["updates"] = True
        write_json_file(CONFIG_PATH, config)
        
        # Apply stashed changes if we stashed them
        if stashed:
            logger.info("Applying stashed changes.")
            try:
                run_subprocess(["git", "stash", "pop"])
                logger.info("✅ Stashed changes applied successfully.")
            except subprocess.CalledProcessError:
                logger.warning("⚠️ Conflict when applying stashed changes. Manual resolution needed.")
        
        return True
    except Exception as e:
        logger.error(f"Repository pull error: {e}")
        return False

def on_updates_change(event):
    """Firebase event handler for updates"""
    if event.data==True:
        logger.info("Update detected in Firebase. Pulling repo itory...")
        pull_repository()

def firebase_listener_loop():
    """Main loop to maintain Firebase listeners"""
    # Load configuration
    config = read_json_file(CONFIG_PATH)
    
    # Initialize Firebase
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout': 30  # Increased timeout for better stability
    })
    
    printer_ref = db.reference(f"Printers/{config['code']}")
    network_error = False
    active_listeners = []
    
    while True:
        try:
            # Clean up old listeners
            for listener in active_listeners:
                try:
                    listener.close()
                except Exception as e:
                    logger.warning(f"Listener close failed: {e}")
            active_listeners.clear()
            
            # Set up new listener
            logger.info("Setting up new Firebase listener...")
            listener = printer_ref.child("updates").listen(on_updates_change)
            active_listeners.append(listener)
            
            # Monitor listener health
            while True:
                time.sleep(30)  # Check every 30 seconds
                if network_error:
                    raise Exception("Network error detected")
                
                for listener in active_listeners:
                    if not listener._thread.is_alive():
                        raise Exception("Listener thread died")
                        
        except Exception as e:
            logger.error(f"Listener loop error: {str(e)}")
            logger.info("Reconnecting in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    # Start the Firebase listener loop
    firebase_listener_loop()