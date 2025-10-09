from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os, time, json, tempfile



cwd = os.getcwd()

with open(os.path.join(cwd, "../secrets/details.json"), "r") as f:
    data = json.load(f)

options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--allow-running-insecure-content")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--unsafely-treat-insecure-origin-as-secure=http://localhost:3000")
options.add_argument("--disable-infobars")
options.add_argument("--start-maximized")
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ["enable-automation"])

# 🧠 Create a unique temp user data directory for this session
user_data_dir = tempfile.mkdtemp()
options.add_argument(f"--user-data-dir={user_data_dir}")

service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

driver.get(f"http://localhost:3000/?code={data['code']}")

while True:
    time.sleep(100)
