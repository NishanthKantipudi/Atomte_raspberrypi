import subprocess
import threading
import queue
import time
import traceback
import json,os
import logging
import firebase_admin
from firebase_admin import credentials, db


def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()



def getcwd():
    cwd = os.getcwd()
    return cwd
cwd=getcwd()
cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'storageBucket': 'skilldevelopmentapp.appspot.com'
})
with open(cwd+"/../secrets/details.json", "r") as f:
    s_data = json.load(f)

import subprocess
import threading
import queue
import time
import traceback

def run_command_with_timeout(command, timeout=30):
    output_queue = queue.Queue()
    error_queue = queue.Queue()
    
    def target():
        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            stdout, stderr = process.communicate()
            output_queue.put(stdout)
            error_queue.put(stderr)
            output_queue.put(process.returncode)
        except Exception as e:
            error_queue.put(str(e))
            output_queue.put(None)
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    
    thread.join(timeout)
    
    if thread.is_alive():
        # Timeout occurred
        return (None, None, f"Command timed out after {timeout} seconds")
    
    try:
        return_code = output_queue.get(block=False)
        stdout = output_queue.get(block=False)
        stderr = error_queue.get(block=False)
        return (return_code, stdout, stderr)
    except queue.Empty:
        return (None, None, "Failed to retrieve command output")

def get_printer_properties(printer_name, timeout=10):
    try:
        command = ["lpoptions", "-p", printer_name, "-l"]
        return_code, stdout, stderr = run_command_with_timeout(command, timeout)
        if return_code is None:
            logger.info(f"Failed to get properties for printer '{printer_name}': {stderr}")
            return None
        if stdout != 0:
            logger.info(f"Error getting printer properties: {stderr}")
            return None
        properties = {}
        for line in return_code.strip().split("\n"):
            parts = line.split()
            if len(parts) > 1:
                option_name = parts[0]
                choices = parts[1:]
                properties[option_name] = choices
        if(len(properties.keys()))==0:
            db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("connection").set("failed")
            return None
        else:
            db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("connection").set("success")
            logger.info("Printer Properties:"+ properties)
            return properties
    except Exception as e:
        logger.info(f"Unexpected error retrieving printer properties: {e}")
        db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("connection").set("failed")
        traceback.print_exc()
        return None
def setup(snap):
    if not snap.data:
        logger.info("No printer setup data provided.")
        return
    try:
        printer_ref = db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process")
        if printer_ref.child("start").get():
            printer_ref.child("start").set(False)
            data = printer_ref.get()
            command = [
                "lpadmin", 
                "-p", data["name"], 
                "-E", 
                "-v", "ipp://"+data['printer_ip']+"/ipp/print", 
                "-m", "everywhere"
            ]
            return_code, stdout, stderr = run_command_with_timeout(command, timeout=15)
            printer_ref.child("status").set("connected-fetching properties")
            if stdout == 0:
                logger.info("Printer added successfully!")
                logger.info("Command Output:"+ str(stdout))
                try:
                    props=get_printer_properties(data["name"])
                    if(props is not None):
                        printer_ref.child("properties").set(props)
                        printer_ref.child("connection").set("success")
                        time.sleep(2)
                        db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup").set(True)
                    else:
                        printer_ref.child("status").set("failed getting options")
                        printer_ref.child("connection").set("failed")
                except Exception as prop_error:
                    printer_ref.child("status").set("failed-"+str(prop_error))
                    printer_ref.child("connection").set("failed")
                    logger.info(f"Error retrieving printer properties: {prop_error}")
            else:
                printer_ref.child("status").set("failed-"+stderr)
                logger.info("Printer addition failed.")
                logger.info("Error Output: "+ stderr)
                printer_ref.child("connection").set("failed")
        else:
            printer_ref.child("status").set("failed")
            logger.info("No active printer setup process found.")
    except Exception as e:
        logger.info("Unexpected error in printer setup:")
        logger.info(traceback.format_exc())
        try:
            printer_ref.child("status").set("failed-"+str(e))
            db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("error").set(str(e))
            db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("connection").set("failed")
        except:
            logger.info("Error in setting printer setup status network error")
            pass
db.reference("/").child("Printers").child(s_data["code"]).child("printer_setup_process").child("start").listen(setup)
