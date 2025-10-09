from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os, time, json, tempfile

cwd = os.getcwd()

with open(os.path.join(cwd, "../secrets/details.json"), "r") as f:
    data = json.load(f)

options = Options()

# --- Stable working flags for Chromium 141 ---
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--allow-running-insecure-content")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-infobars")
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")
options.add_argument("--start-fullscreen")
options.add_argument("--kiosk")  # kiosk still works on 141
options.add_argument("--hide-scrollbars")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-features=TranslateUI,AutomationControlled,RendererCodeIntegrity")
options.add_argument("--unsafely-treat-insecure-origin-as-secure=http://localhost:3000")

# Disable automation banners in 141 (new way)
options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
options.add_experimental_option("prefs", {
    "profile.default_content_setting_values.media_stream_mic": 1,
    "profile.default_content_setting_values.media_stream_camera": 1,
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False
})

# Unique user profile for this session
user_data_dir = tempfile.mkdtemp()
options.add_argument(f"--user-data-dir={user_data_dir}")

# Path to ChromeDriver
service = Service("/usr/bin/chromedriver")

# 🧠 Create driver
driver = webdriver.Chrome(service=service, options=options)

# Load your app
driver.get(f"http://localhost:3000/?code={data['code']}")

# Force fullscreen with JavaScript (extra layer of reliability)
driver.fullscreen_window()

while True:
    time.sleep(100)
