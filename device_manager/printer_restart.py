from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import os,json
import firebase_admin
from firebase_admin import credentials, db
import time

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
from selenium.webdriver.chrome.service import Service
service=Service(executable_path='/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service,options=chrome_options)
# driver = webdriver.Chrome()
cwd = os.getcwd()
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data
main_data = read_json_file(cwd+"/../secrets/details.json")
cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'httpTimeout':10
})
printer_ref = db.reference("Printers/"+main_data["code"])
ip = printer_ref.child("details").child("ip").get()
dns_name = printer_ref.child("details").child("dns_name").get()
if(dns_name==None or dns_name==""):
    driver.get("http://"+dns_name+".local"+":8000/usermode")
else:
    driver.get("http://"+ip+":8000/usermode")
time.sleep(1)
restart_button = driver.find_element(By.XPATH, "//input[@value='Restart Device ']")
restart_button.click()
time.sleep(1)
restart_button = driver.find_element(By.XPATH, "//input[@value='Perform Restart']")
restart_button.click()
time.sleep(1)
alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
alert.accept()
printer_ref.child("restart_printer").set(False)