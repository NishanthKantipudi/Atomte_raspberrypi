#!/usr/bin/env python3
import os
import subprocess
import configparser
import sys
import logging

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()


class WiFiHotspot:
    def __init__(self, ssid, password, interface="wlan0"):
        self.ssid = ssid
        self.password = password
        self.interface = interface
        
    def check_dependencies(self):
        """Check if required packages are installed"""
        required_packages = ['hostapd', 'dnsmasq']
        missing_packages = []
        
        for package in required_packages:
            result = subprocess.run(['dpkg', '-s', package], capture_output=True, text=True)
            if result.returncode != 0:
                missing_packages.append(package)
                
        if missing_packages:
            logger.info(f"Missing required packages: {', '.join(missing_packages)}")
            logger.info("Installing missing packages...")
            os.system(f"sudo apt-get update && sudo apt-get install -y {' '.join(missing_packages)}")

    def create_hostapd_config(self):
        """Create hostapd configuration file"""
        config = f"""
interface={self.interface}
driver=nl80211
ssid={self.ssid}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={self.password}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
"""
        with open('/tmp/hostapd.conf', 'w') as f:
            f.write(config.strip())
        os.system('sudo mv /tmp/hostapd.conf /etc/hostapd/hostapd.conf')

    def create_dnsmasq_config(self):
        """Create dnsmasq configuration file"""
        config = f"""
interface={self.interface}
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=wlan
address=/gw.wlan/192.168.4.1
"""
        with open('/tmp/dnsmasq.conf', 'w') as f:
            f.write(config.strip())
        os.system('sudo mv /tmp/dnsmasq.conf /etc/dnsmasq.conf')

    def configure_network(self):
        """Configure network interface"""
        os.system('sudo systemctl stop dhcpcd')
        os.system(f'sudo ifconfig {self.interface} 192.168.4.1/24')
        
        # Enable IP forwarding
        with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
            f.write('1')
            
        # Set up NAT
        os.system('sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE')

    def start_services(self):
        """Start hostapd and dnsmasq services"""
        os.system('sudo systemctl unmask hostapd')
        os.system('sudo systemctl enable hostapd')
        os.system('sudo systemctl start hostapd')
        os.system('sudo systemctl start dnsmasq')

    def setup_hotspot(self):
        """Main method to set up the hotspot"""
        if os.geteuid() != 0:
            logger.info("This script must be run as root!")
            sys.exit(1)
            
        logger.info("Setting up Wi-Fi hotspot...")
        self.check_dependencies()
        self.create_hostapd_config()
        self.create_dnsmasq_config()
        self.configure_network()
        self.start_services()
        logger.info(f"\nHotspot setup complete!")
        logger.info(f"SSID: {self.ssid}")
        logger.info(f"Password: {self.password}")
        logger.info("IP Address: 192.168.4.1")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        logger.info("Usage: sudo python3 hotspot.py <ssid> <password>")
        sys.exit(1)
        
    hotspot = WiFiHotspot(sys.argv[1], sys.argv[2])
    hotspot.setup_hotspot()