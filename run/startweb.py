from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import json

# Get current working directory
cwd = os.getcwd()

# Load secrets
with open(os.path.join(cwd, "../secrets/details.json"), "r") as f:
    data = json.load(f)

# Chrome options
options = Options()
options.binary_location = "/snap/bin/chromium"
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--kiosk")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--allow-running-insecure-content")
options.add_argument("--unsafely-treat-insecure-origin-as-secure=http://localhost:3000")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_argument("--disable-infobars")
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ["enable-automation"])

# Correct way to use webdriver-manager
driver_path = ChromeDriverManager().install()  # <-- just call install()
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Open React website
driver.get("http://localhost:3000/?code=" + data["code"])

# Keep running
while True:
    time.sleep(100)

