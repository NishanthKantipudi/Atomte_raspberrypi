from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import tempfile
# Configure Chromium options
chrome_options = Options()
chrome_options.binary_location = "/usr/bin/chromium-browser"
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--headless")  # Remove this line if you want to see the browser
temp_user_data_dir = tempfile.mkdtemp()
chrome_options.add_argument(f"--user-data-dir={temp_user_data_dir}")
# Explicitly set Chromedriver path
service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)


try:
    # Step 1: Open the site
    driver.get("http://192.168.2.80:8000/usermode")

    # Step 2: Wait and click the first button with class = ButtonEnable
    first_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "ButtonEnable"))
    )
    first_button.click()

    # Step 3: Wait for new page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "ContentOperation"))
    )

    # Step 4: Inside ContentOperation div, click the ButtonEnable button
    content_div = driver.find_element(By.CLASS_NAME, "ContentOperation")
    second_button = content_div.find_element(By.CLASS_NAME, "ButtonEnable")

    # Step 5: Click it
    second_button.click()

    print("? Successfully clicked both buttons!")
    time.sleep(2)  # short wait for dialog to appear

    try:
        # --- Try handling a JavaScript alert ---
        alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
        print("??  JavaScript alert detected.")
        alert.accept()  # click OK
        print("? Clicked OK on alert dialog")

    except:
        # --- If not JS alert, look for HTML dialog ---
        print("??  No JavaScript alert found. Checking for HTML dialog...")
        try:
            ok_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()='OK' or text()='Ok' or text()='ok']"))
            )
            ok_button.click()
            print("? Clicked OK on HTML dialog")
        except:
            print("??  No dialog detected to click OK.")

    print("? All steps completed successfully!")

except Exception as e:
    print("? Error:", e)
time.sleep(10)

driver.quit()

import shutil
shutil.rmtree(temp_user_data_dir, ignore_errors=True)