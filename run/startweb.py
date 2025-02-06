from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

def getcwd():
    cwd = os.getcwd()
    return cwd
cwd=getcwd()

import json
with open(cwd+"/../secrets/details.json", "r") as f:
    data = json.load(f)
options = Options()
options.add_argument("--autoplay-policy=no-user-gesture-required")  # Allow autoplay with sound
options.add_argument("--use-fake-ui-for-media-stream")  # Bypass media permission prompts
options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent detection
options.add_argument("--disable-infobars")  # Disable infobars
options.add_argument("--kiosk")  # Enable kiosk mode
# Set up WebDriver
service = Service("/usr/bin/chromedriver")  # Path to ChromeDriver
driver = webdriver.Chrome(service=service, options=options)

# Open the React website
driver.get("http://localhost:3000/?code="+data["code"])  # 