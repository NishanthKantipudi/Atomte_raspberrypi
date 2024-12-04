
import firebase_admin
from firebase_admin import credentials, db,messaging
import os
import time
import threading
import PyPDF2
import asyncio
import math
import tempfile
from pysnmp.hlapi.v1arch.asyncio import *
import cups
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image
import razorpay
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import socket
import json
import multiprocessing
# from deepgram import (
#     DeepgramClient,
#     SpeakOptions,
# )


p_error=True
i_error=True


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=1)

cwd = os.getcwd()

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data
main_data = read_json_file(cwd+"/../secrets/details.json")
main_data["printer_id"] = main_data["code"]
async def int_check():
    global i_error
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            # requests.post("http://localhost:5000/update_data", json={"message":"internet connected"})
            i_error=False
            break
        except OSError:
            i_error=True
            # requests.post("http://localhost:5000/update_data", json={"message":"no internet"})
            await asyncio.sleep(1)
asyncio.run(int_check())

def check_i_error_p_error():
    global i_error
    global p_error
    while 1:
        try:
            if not (i_error or p_error):
                requests.post("http://localhost:5000/update_data", json={"message":"internet connected"})
            else:
                requests.post("http://localhost:5000/update_data", json={"message":"no internet"})
            time.sleep(3)
        except OSError:
            logger.error("check internet error-error sending message to web")
       
# check_i_error_p_error_thread = threading.Thread(target=check_i_error_p_error)
# check_i_error_p_error_thread.daemon = True
# check_i_error_p_error_thread.start()

cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
    'httpTimeout':10
})


def get_ip_from_mdns(hostname):
    global p_error
    while 1:
        try:
            ip_address = socket.gethostbyname(hostname)
            printer_ref.child("details").child("ip").set(ip_address)
            return ip_address
        except Exception as e:
            print(f"Error resolving mDNS name: {e}")
            p_error=True
            time.sleep(1)
ip_address = ""
dns_name=""
async def init_firebase():
    global i_error
    global printer_ref,ip,printer_name,dns_name,ip_address
    while 1:
        try:
            printer_ref = db.reference("Printers/"+main_data["printer_id"])
            # printer_ref.child("details").child("ip").set(ip_address)
            printer_ref.child("details").child("status_message").set("Fetching ip address")
            printer_ref.child("details").child("status").set("Inactive")
            dns_name=printer_ref.child("details").child("dns_name").get()
            printer_name="nishanth1"
            ip_address = printer_ref.child("details").child("ip").get()#get_ip_from_mdns(dns_name+".local")
            ip=ip_address
            printer_ref.child("details").child("status_message").set("Fetched ip address")
            i_error=False
            break
        except Exception as e:
            i_error=True
            time.sleep(3)
            logger.error('get ip failed'+str(e))
asyncio.run(init_firebase())
key = 'rzp_live_7p3oO9G6VYLXcd'
secret = 'aEIdELoJ4GIDf03DqpfVrGpX'
try:
    client = razorpay.Client(auth=(key, secret))
    # deepgram = DeepgramClient(api_key="b3473b8ababc16dd50a450145a8b01fc87fb558a")
    # options = SpeakOptions(
    #         model="aura-asteria-en",
    #         encoding="linear16",
    #         container="wav"
    #     )
except Exception as e:
    logger.error('razorpay client error '+str(e))
conn = cups.Connection()
printers = conn.getPrinters()
printer_name = printer_ref.child("details").child("name").get()

jobs = conn.getJobs()

for job_id, job_info in jobs.items():
    conn.cancelJob(job_id)

for job_id, job_info in jobs.items():
    job_state = job_info.get("job-state", None)
    job_state_reasons = job_info.get("job-state-reasons", "")
    logger.info(f"{job_id}")
    # CUPS job state 3 indicates 'pending'
    if job_state == 3:
        logger.info(f"Job ID: {job_id}, Title: {job_info['job-name']}, User: {job_info['job-originating-user-name']}, State: Pending, Reason: {job_state_reasons}")
        print(f"Job ID: {job_id}, Title: {job_info['job-name']}, User: {job_info['job-originating-user-name']}, State: Pending")
else:
    logger.info("no jobs")
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def update_database(user, filename, progress_percentage):
    try:
        db.reference(f'users/{user}/printsdetails/{filename}').child("printprogress").set(progress_percentage)
    except Exception as e:
        logger.error('progress set error '+str(e))

def convert_to_pdf(image_path, pdf_path):
    with Image.open(image_path) as img:
        img.convert("L").save(pdf_path, "PDF",optimize=True, resolution=80.0)
def send_high_priority_notification(token,title="",body="",data={}):
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
            android=messaging.AndroidConfig(
                priority="high"
            ),
            data=data
        )
        try:
            response = messaging.send(message)
            logger.info(f'Successfully sent message: {response}')
        except Exception as e:
            logger.error(f"Error sending message: {e}")

def get_print_job_state(conn, print_job_id):
    try:
        job_attributes = conn.getJobAttributes(print_job_id)
        job_state = job_attributes.get("job-state")
        job_state_reasons = job_attributes.get("job-state-reasons", "unknown")
        job_state_mapping = {
            3: "Pending",
            4: "Held",
            5: "Processing",
            6: "Stopped",
            7: "Canceled",
            8: "Aborted",
            9: "Completed"
        }
        state_description = job_state_mapping.get(job_state, "Unknown")
        return state_description, job_state_reasons
    except cups.IPPError as e:
        print(f"Failed to get job state: {e}")
        return None, None
def print_file(user, file):
    file_data = db.reference(f'users/{user}/printsdetails/{file}').get()
    if file_data["count"]==0:
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Done")
        return 0
    db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Downloading file...")
    db.reference(f'users/{user}/printsdetails/{file}').child("printprogress").set(0)
    try:
        filename = "files/"+user+"/"+file
    except Exception as e:
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error downloading file")
        logger.error(f"Error downloading file: {e}")
        raise Exception("Error downloading file")
    logger.info("File downloaded")
    db.reference(f'users/{user}/printsdetails/{file}').child("status").set("File downloaded, starting printing...")
    n_up=int(file_data["properties"]["count_per_page"].split(" ")[0])
    orientation = 'landscape' if file_data["properties"]["zedge"] == "Horizontal" else 'portrait'
    binding = 'Top' if file_data["properties"]["zedge"] == "Horizontal" else 'Left'
    options = {
        "copies": str(file_data["count"]),
        "number-up": str(n_up),
        "media":"ISO A4",
        "sides": (
            'two-sided-short-edge' if file_data["properties"]["zedge"] == "Horizontal" and file_data["properties"]["sides"] != "Single-sided"
            else 'two-sided-long-edge' if file_data["properties"]["sides"] != "Single-sided"
            else 'single-sided'
        ),
        "orientation-requested": orientation,
        'BindEdge': binding
    }
    timestamp = str(int(time.time()))
    try:
        print_job_id = conn.printFile(printer_name, os.path.abspath(filename), timestamp, options)
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("printing...")
        return 1
        while True:
            state_description, state_reasons = get_print_job_state(conn, print_job_id)
            print(f"Print Job State: {state_description}")
            if state_reasons:
                print(f"State Reasons: {state_reasons}")
                return 1
            if state_description == "Completed":
                # Update the database status to "Done"
                db.reference(f'users/{user}/printsdetails/{file}').child("status").set("printing...")
                print("Print job completed. Status set to 'Done'.")
                logger.info(f"Print job ID: {print_job_id}")
                return 1
            elif state_description in ["Canceled", "Aborted", "Stopped"]:
                print("Print job did not complete successfully.")
                db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
                logger.info('Error at printer')
                
                return 0
            time.sleep(0.5)
        # db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Done")
    except Exception as e:
        try:
            db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
        except Exception as e:
            logger.error(f"Error at set status: {e}")
        logger.error(f"Error at printer: {e}")
        raise Exception("Error at printer")
    logger.info(f"Print job ID: {print_job_id}")
    return 1

curr_page_count=0

async def query_snmp_data(snmpDispatcher, oid, ip):
    try:
        async def snmp_query():
            return await getCmd(
                snmpDispatcher,
                CommunityData("public", mpModel=0),
                await UdpTransportTarget.create((ip, 161), timeout=3, retries=2),
                ObjectType(ObjectIdentity(oid))
            )

        # Use asyncio.wait_for to enforce a timeout
        try:
            iterator = await asyncio.wait_for(snmp_query(), timeout=5)  # Set your desired timeout
        except asyncio.TimeoutError:
            # logger.error(f"SNMP query timed out for OID: {oid}")
            raise Exception("SNMP query timed out")

        # logger.info("SNMP data queried successfully")

        errorIndication, errorStatus, errorIndex, varBinds = iterator

        if errorIndication:
            logger.error(f"SNMP Error: {errorIndication}")
            raise Exception("Error querying SNMP data")
        elif errorStatus:
            logger.error(f"Error Status: {errorStatus.prettyPrint()} at {errorIndex}")
            raise Exception("Error querying SNMP data")
        else:
            # logger.info(f"SNMP data: {varBinds[0][1].prettyPrint()}")
            return varBinds[0][1].prettyPrint()
    except Exception as e:
        logger.error(str(e))

        raise

async def get_snmp_data():
    global p_error,ip,i_error
    global curr_page_count
    snmpDispatcher = SnmpDispatcher()
    target = ip # Your printer's IP address
    # target = dns_name+".local"
    community = "public"
    oids = {
        "Printer Detailed Status": "1.3.6.1.2.1.43.16.5.1.2.1.1",
        "printed": "1.3.6.1.2.1.43.10.2.1.4.1.1",
        "toner level": "1.3.6.1.2.1.43.11.1.1.9.1.1",
        "tray 1": "1.3.6.1.2.1.43.8.2.1.10.1.2",  
        "tray 2": "1.3.6.1.2.1.43.8.2.1.10.1.3", 
    }
    conn_error=False
    no_papers=False
    paper_jammed=False
    no_toner=False
    e_c=0
    while True:  # Continuous loop
        target = ip
        try:
            results = {}
            for key, oid in oids.items():
                result = await query_snmp_data(snmpDispatcher, oid,target)
                if result is not None:
                    results[key] = result
                    p_error=False
                else:
                    p_error=True
                    print(f"Failed to retrieve data for {key}")
                    results[key] = "Error"
            if(results['printed']!="Error"):
                printer_ref.child("details").child("pages_printed").set(results['printed'])
                curr_page_count=results['printed']
                printer_ref.child("details").child("tray_1").set(results['tray 1'])
                printer_ref.child("details").child("tray_2").set(results['tray 2'])
                printer_ref.child("details").child("toner_level").set(results['toner level'])
            time.sleep(1)
            e_c=0
            if conn_error:
                conn_error=False
                if(printer_ref.child("details").child("status_message").get()=="printer is restarting network issue at fetching data"):
                    printer_ref.child("details").child("status").set("Active")
                    printer_ref.child("details").child("status_message").set("Printer is Active")
            if 'toner is out (black).' in results['Printer Detailed Status']:
                
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("toner is empty...")
            if results['tray 1'] == "0" and results['tray 2'] == "0":
                
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("Printer is empty please wait for a while")
                no_papers=True
            if no_papers:
                if results['tray 1'] != "0" or results['tray 2'] != "0":
                    if(printer_ref.child("details").child("status_message").get()=="Printer is empty please wait for a while"):
                        printer_ref.child("details").child("status").set("Active")
                        printer_ref.child("details").child("status_message").set("Printer is Active")
                    no_papers=False
            if paper_jammed:
                if "paper jam" not in results['Printer Detailed Status'].lower():
                    if (printer_ref.child("details").child("status_message").get()=="Paper is jammed please wait for a while"):
                        printer_ref.child("details").child("status").set("Active")
                        printer_ref.child("details").child("status_message").set("Printer is Active")
                        paper_jammed=False
            if no_toner:
                if "empty" in results['Printer Detailed Status'].lower() and "toner" in results['Printer Detailed Status'].lower():
                    if (printer_ref.child("details").child("status_message").get()=="Toner is empty takes 10-100mins to refill"):
                        printer_ref.child("details").child("status").set("Active")
                        printer_ref.child("details").child("status_message").set("Printer is Active")
                        no_toner=False
            if "paper jam" in results['Printer Detailed Status'].lower():
                
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("Paper is jammed please wait for a while")
                printer_ref.child("details").child("error").set("Paper is jammed")
                paper_jammed=True
            elif "empty" in results['Printer Detailed Status'].lower() and "toner" in results['Printer Detailed Status'].lower():
                
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("Toner is empty takes 10-100mins to refill")
                printer_ref.child("details").child("error").set("Toner is empty")
                no_toner=True
            else:
                printer_ref.child("details").child("error").set(results['Printer Detailed Status'])
        except Exception as e:
            # p_error=True
            e_c+=1
            if e_c>5:
                p_error=True
                e_c=0
                try:
                    printer_ref.child("details").child("status").set("Inactive")
                    printer_ref.child("details").child("status_message").set("printer is restarting network issue at fetching data")
                    conn_error=True
                except Exception as e1:
                    i_error=True
                    logger.error("Failed to update printer status: " + str(e1))
                ip=get_ip_from_mdns(dns_name+".local")
            logger.error("Unexpected Error in main loop: " + str(e))
            time.sleep(3)
def run_snmp_loop():
    asyncio.run(get_snmp_data())
server_thread = threading.Thread(target=run_snmp_loop)
server_thread.daemon = True
server_thread.start()

pr=""
def on_value_change(event):
    global pr
    data = db.reference(f'Printers/{main_data["printer_id"]}/printstodo').get()
    if data is not None:
        keys = list(data.keys())
        if keys:
            first_key = keys[0]
            if pr != first_key:
                pr = first_key 
                print(f"New data for {first_key}: {data[first_key]}")
                on_value_change1(first_key,data[first_key])
            

def on_value_change1(event_key,data):
    global p_error,i_error
    try:
        if event_key:
            data = db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').get()
            if data:
                init_page_count = curr_page_count
                pc = 0
                files = data["files"]
                f = files
                files = files.split(",")
                user = data["user"]
                printing_pages = []
                i=0
                def l1():
                    count = 1
                    nonlocal pc, printing_pages
                    try:
                        for file in files:
                            db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("printing").set(count)
                            db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("done_printing").set(i)
                            db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("user").set(user)
                            db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("files").set(f)
                            logger.info(f"Printing: {file}")
                            try:
                                p = print_file(user, file) 
                                if p:
                                    up_c = int(db.reference(f'users/{user}/printsdetails/{file}/properties').child('count_per_page').get().split(" ")[0])
                                    total_pc = math.ceil(db.reference(f'users/{user}/printsdetails/{file}').child('pagecount').get() / up_c) * db.reference(f'users/{user}/printsdetails/{file}').child('count').get()
                                    pc += total_pc
                                    printing_pages.append(pc)
                                else:
                                    printing_pages.append(pc)
                            except Exception as e:
                                printing_pages.append(pc)
                                logger.error(f"Error at printing {file}: {e}")
                            count += 1
                        logger.info("Sent to printer")
                    except Exception as e:
                        logger.error(f"Error in print thread: {e}")
                t1 = threading.Thread(target=l1)
                t1.daemon = True
                t1.start()
                printed_sum=0
                while True:
                    pages_printed = int(curr_page_count) - int(init_page_count)
                    if(len(printing_pages)<=i):
                        continue
                    db.reference(f'users/{user}/printsdetails/{files[i]}').child("printed").set(f"{pages_printed-printed_sum}/{printing_pages[i]-printed_sum}")
                    if pages_printed >= printing_pages[i]:
                        printed_sum=printing_pages[i]
                        db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("Done printing")
                        db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("done_printing").set(i+1)
                        i = i + 1
                        if i == len(files):
                            db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').delete()
                            break
                    if p_error or i_error:
                        
                        logger.error('Error at page count diff p_error')
                        break
                    time.sleep(1)
    except Exception as e:
        time.sleep(3)
        logger.error('error value listner'+str(e))
        t1.terminate()
        try:
            db.reference(f'Printers/123456/printstodo/{event_key}').delete()
        except Exception as e:
            raise Exception("Error at listner")

def check_network():
    global i_error
    c=0
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            # requests.post("http://localhost:5000/update_data", json={"message":"internet connected"})
            c=0
            i_error=False
            time.sleep(5)
        except Exception as e:
            c+=1
            if(c==3):
                c=0
                logger.error("check network ------------------ error : "+str(e))
                # requests.post("http://localhost:5000/update_data", json={"message":"internet not connected"})
                i_error=True
            logger.error("check network error : "+str(p_error)+str(e))
            time.sleep(5)
server_thread1 = threading.Thread(target=check_network)
server_thread1.daemon = True
server_thread1.start()

async def main():
    global p_error,i_error
    listners=[]
    ref = db.reference(f'Printers/{main_data["printer_id"]}/printstodo')
    while True:
        try:
            response = requests.get("http://"+str(ip_address)+":8000",timeout=5)
            printer_ref.child("details").child("status").set("InActive")
            printer_ref.child("details").child("status_message").set("tring to connect..")
            logger.info("tring to connect..."+str(response.status_code))
            if response.status_code == 200:
                for listner in listners:
                    listner.close()
                listners=[]
                printer_ref.child("details").child("status").set("Active")
                printer_ref.child("details").child("status_message").set("Printer is Active")
                logger.info("Connected")
                i_error=False
                listner=ref.listen(on_value_change)
                listners.append(listner)
                # await broadcast_message("printer is ready to print")
                while True:
                    for listner in listners:
                        if(listner._thread.is_alive()):
                            continue
                        else:
                            raise Exception("listner error")
                    if(i_error or p_error):
                        # await broadcast_message("printer is not ready to print")
                        logger.error('error i_error or p_error'+str(i_error)+str(p_error))
                        for listner in listners:
                            listner.close()
                        listners=[]
                        raise Exception("i_error or p_error")
                    # await broadcast_message("printer is ready to print")
                    time.sleep(3)
            else:
                for listner in listners:
                    listner.close()
                listners=[]
                logger.info("connecting..")
                printer_ref.child("details").child("status_message").set("connecting...")
                # await broadcast_message("printer is not ready to print")
                time.sleep(5)
                continue
        except Exception as e:
            # await broadcast_message("printer is not ready to print")
            logger.error(f"Error in main loop: {e}")
            if(i_error or p_error):
                logger.error(f"Error in main loop: {e}") 
                time.sleep(3)
                for listner in listners:
                    listner.close()
                listners=[]
                continue
            try:
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("something went wrong,tring to reconnect")
                logger.error(f"Error in main loop: {e}") 
                
            except Exception as e:
                logger.error("error at main exception "+str(e))
            time.sleep(5)
if __name__ == "__main__":
    asyncio.run(main())