#import modules
import os
import subprocess
import pexpect
import logging

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Put cwd as ~/Atomte/
cwd = os.path.expanduser("~/Atomte/")

def run_subprocess(command, shell=False):
    """Run a subprocess command and return the result"""
    try:
        if isinstance(command, list):
            result = subprocess.run(command, capture_output=True, text=True, check=True, shell=shell)
        else:
            result = subprocess.run(command, capture_output=True, text=True, check=True, shell=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return None

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
        result = run_subprocess(["ssh-keyscan", "-t", "rsa", "github.com"], shell=False)
        
        if result:
            with open(known_hosts_file, 'a') as f:
                f.write(result)
            logger.info("GitHub host key added to known_hosts")
            return True
        else:
            logger.error("Failed to get GitHub host key")
            return False
    except Exception as e:
        logger.error(f"Error adding GitHub to known_hosts: {e}")
        return False

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
        
        # Set proper permissions on SSH key
        ssh_key_path = os.path.join(cwd, "SSH/ssh_key")
        run_subprocess(["chmod", "600", ssh_key_path])
        
        # Add GitHub to known_hosts
        if not add_github_to_known_hosts():
            logger.warning("Failed to add GitHub to known_hosts. Host verification might fail.")
        
        # Add SSH key
        return add_ssh_key("8985")
    except Exception as e:
        logger.error(f"SSH setup error: {e}")
        return False

def add_ssh_key(passphrase):
    try:
        if 'SSH_AUTH_SOCK' not in os.environ:
            raise Exception("SSH agent not running")
        child = pexpect.spawn(f'ssh-add {cwd}/SSH/ssh_key')
        child.expect('Enter passphrase', timeout=5)
        child.sendline(passphrase)
        child.expect(pexpect.EOF)
        logger.info("SSH key added successfully")
        return True
    except Exception as e:
        logger.error(f"SSH key error: {e}")
        return False

def pull_repository():
    if setup_ssh():
        try:
            # Check if repository exists
            repo_dir = os.path.join(cwd, "Atomte_raspberrypi")
            if os.path.exists(repo_dir):
                # If it exists, pull the latest changes
                logger.info("Repository exists, pulling latest changes...")
                result = run_subprocess(f"cd {repo_dir} && git pull")
            else:
                # Clone the repository
                logger.info("Cloning repository...")
                # Adding StrictHostKeyChecking=no as a fallback
                result = run_subprocess(f"GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=accept-new' git clone --depth=1 git@github.com:NishanthKantipudi/Atomte_raspberrypi.git {repo_dir}")
                logger.info("✅ Git operation completed successfully.")
          
        except Exception as e:
            logger.error(f"Repository pull error: {e}")
            
    else:
        logger.error("SSH setup failed, cannot pull repository")
       

def main():
    logger.info("Starting repository pull process...")
    pull_repository()
    logger.info("Repository pull completed successfully")
    
if __name__ == "__main__":
    main()