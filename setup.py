#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import paramiko
import argparse
from scp import SCPClient
import json

def run_local_command(command):
    """Run a command on the local machine and return its output"""
    print(f"Executing locally: {command}")
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
    return result.stdout.strip()

def create_ssh_client(hostname, username, password):
    """Create and return an SSH client"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Try to connect a few times in case of network issues
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            print(f"Connecting to {username}@{hostname} (attempt {attempt+1}/{max_attempts})...")
            client.connect(hostname=hostname, username=username, password=password)
            print("Connected successfully!")
            return client
        except Exception as e:
            print(f"Connection attempt {attempt+1} failed: {e}")
            if attempt < max_attempts - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Max connection attempts reached. Exiting.")
                sys.exit(1)

def run_remote_command(ssh_client, command, sudo=False):
    """Run a command on the remote machine and print its output"""
    full_command = command
    if sudo:
        # Use echo to provide the password to sudo
        full_command = f'echo "{RPI_PASSWORD}" | sudo -S {command}'
    
    print(f"Executing on Raspberry Pi: {command}")
    stdin, stdout, stderr = ssh_client.exec_command(full_command)
    
    # Print output in real-time
    for line in stdout:
        print(f"  {line.strip()}")
    
    # Check for errors
    error = stderr.read().decode().strip()
    if error:
        print(f"Command produced error: {error}")
    
    # Return exit status
    return stdout.channel.recv_exit_status()

def transfer_files(ssh_client, local_path, remote_path):
    """Transfer files from local to remote using SCP"""
    print(f"Transferring {local_path} to {remote_path}")
    with SCPClient(ssh_client.get_transport()) as scp:
        scp.put(local_path, remote_path)

def update_code(new_code):
    path = f"./details.json"
    with open(path, 'r') as f:
        data = json.load(f)
    data['code'] = str(new_code)
    data['pi_username'] = f"atomte{new_code}"
    data['pi_hostname'] = f"atomte{new_code}"
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    return True

def main():
    parser = argparse.ArgumentParser(description="Automate Raspberry Pi setup for Atomte")
    parser.add_argument("code", help="The code number (e.g., 100005)")
    args = parser.parse_args()
    
    code = args.code
    global RPI_PASSWORD
    RPI_PASSWORD = "7093812229"  # Raspberry Pi login password
    SSH_KEY_PASSWORD = "8985"     # Password for the SSH key
    
    # Step 1: Find Raspberry Pi IP
    hostname = f"atomte{code}.local"
    print(f"Finding IP address for {hostname}...")
    rpi_ip = run_local_command(f"ping -c 1 {hostname} | awk -F'[()]' '/PING/{{print $2}}'")
    
    if not rpi_ip:
        print(f"Could not find IP address for {hostname}. Make sure the Raspberry Pi is online.")
        sys.exit(1)
    
    print(f"Found Raspberry Pi at IP: {rpi_ip}")
    
    # Step 2: Remove known host entry
    run_local_command(f"ssh-keygen -R {rpi_ip}")
    
    # Step 3: Create SSH connection
    username = f"atomte{code}"
    ssh_client = create_ssh_client(rpi_ip, username, RPI_PASSWORD)
    
    # Step 4: Run initial directory setup commands on Raspberry Pi
    commands = [
        "mkdir -p Atomte/SSH Atomte/boot_image Atomte/secrets Atomte/setup",
        "python3 -m venv Atomte/venv",
        "cd Atomte/SSH"
    ]
    
    for cmd in commands:
        run_remote_command(ssh_client, cmd)
    
    # Step 5: Transfer files from Mac to Raspberry Pi

    update_code(code)
    local_files = {
        f"{os.path.expanduser('~/Desktop/Atomte/Atomte_raspberrypi/Atomte.png')}": f"/home/{username}/Atomte/boot_image/logo.png",
        f"{os.path.expanduser('~/Desktop/Atomte/Atomte_raspberrypi/ssh_key')}": f"/home/{username}/Atomte/SSH/ssh_key",
        f"{os.path.expanduser('~/Desktop/Atomte/Atomte_raspberrypi/ssh_key.pub')}": f"/home/{username}/Atomte/SSH/ssh_key.pub",
        f"{os.path.expanduser('~/Desktop/Atomte/Atomte_raspberrypi/details.json')}": f"/home/{username}/Atomte/secrets/details.json",
        f"{os.path.expanduser('~/Desktop/Atomte/Atomte_raspberrypi/requirements.txt')}": f"/home/{username}/Atomte/setup/requirements.txt",
        f"{os.path.expanduser('~/Desktop/Atomte/Atomte_raspberrypi/setup_raspberrypi.py')}": f"/home/{username}/Atomte/setup/setup.py"
    }
    
    for local_path, remote_path in local_files.items():
        transfer_files(ssh_client, local_path, remote_path)
    
    # Step 6: Run package installation and setup on Raspberry Pi
    setup_commands = [
        "sudo apt update",
        "sudo apt install -y libcups2-dev python3-dev build-essential",
        "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -",
        "sudo apt install -y nodejs",
        "sudo apt install -y sshpass",
        "sudo apt install -y chromium-chromedriver",
        "sudo apt install -y jq",
        "sudo apt install -y git",
        "sudo apt-get install -y wmctrl",
        "sudo apt install -y portaudio19-dev",
        "sudo apt install -y cups",
        "sudo apt install -y tesseract-ocr",
        "sudo apt install -y libtesseract-dev",
        "sudo nmcli connection add type ethernet ifname eth0 con-name eth0 ipv4.method manual ipv4.addresses 192.168.2.1/24",
        "sudo ip link set eth0 up",
        "sudo nmcli con mod eth0 connection.autoconnect yes",
        "sudo ip addr add 192.168.2.1/24 dev eth0",
        "cd Atomte && chmod 600 SSH/ssh_key",
        "Atomte/venv/bin/pip install -r Atomte/setup/requirements.txt",
        "Atomte/venv/bin/python3 Atomte/setup/setup.py",
        "echo 'SUBSYSTEMS==\"usb\", DRIVERS==\"usbhid\", ACTION==\"add\", ATTR{authorized}=\"0\"' | sudo tee /etc/udev/rules.d/99-com.rules",
        "sudo sed -i '/^#*PermitRootLogin/c\\PermitRootLogin no' /etc/ssh/sshd_config && sudo systemctl restart ssh",
        "sudo cp /home/$USER/Atomte/boot_image/logo.png /usr/share/plymouth/themes/pix/splash.png",
        "sudo plymouth-set-default-theme -R pix",
        "sudo update-initramfs -u",
        "sudo iw dev wlan0 set power_save off",
        "sudo usermod -a -G input $USER",
        ('printf "SUBSYSTEMS==\\"usb\\", ATTRS{idVendor}==\\"0218\\", ATTRS{idProduct}==\\"0210\\", ATTR{authorized}=\\"1\\"\\n'
            'SUBSYSTEMS==\\"usb\\", DRIVERS==\\"rndis_host\\", ATTR{authorized}=\\"1\\"\\n'
            'SUBSYSTEMS==\\"usb\\", DRIVERS==\\"cdc_ether\\", ATTR{authorized}=\\"1\\"\\n'
            'SUBSYSTEMS==\\"usb\\", DRIVERS==\\"usbnet\\", ATTR{authorized}=\\"1\\"\\n'
            'SUBSYSTEMS==\\"usb\\", ATTRS{idVendor}==\\"1d6b\\", ATTR{authorized}=\\"1\\"\\n'
            'SUBSYSTEMS==\\"usb\\", DRIVERS==\\"usbhid\\", ATTR{authorized}=\\"0\\"\\n'
            '| sudo tee /etc/udev/rules.d/20-usb-scanner.rules > /dev/null && '
            'sudo update-initramfs -u && sudo udevadm control --reload-rules && sudo udevadm trigger')
            ,
        "sudo sed -i '/^dtoverlay=disable-bt$/!s/^$/dtoverlay=disable-bt/' /boot/firmware/config.txt",
        "(crontab -l 2>/dev/null; echo \"@reboot sudo Atomte/venv/bin/python3 Atomte/Atomte_raspberrypi/run/main.py >> Atomte/Atomte_raspberrypi/run/main.log 2>&1\") | crontab -",
        "sudo reboot"
    ]
    
    for cmd in setup_commands:
        if cmd.startswith("sudo"):
            run_remote_command(ssh_client, cmd[5:], sudo=True)
        else:
            run_remote_command(ssh_client, cmd)
    
    ssh_client.close()
    print("Automation complete. Raspberry Pi will now reboot and start the application.")

if __name__ == "__main__":
    main()