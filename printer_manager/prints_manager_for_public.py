i_error=False
p_error=False
import datetime
import firebase_admin
from firebase_admin import credentials, db,messaging
import os
import time
import threading
import asyncio
import math
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


def init_setup():
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
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            break
        except OSError:
            time.sleep(1)
            logger.info("No internet connection. Retrying in 1 second...")
    
    cred = credentials.Certificate(cwd+"/secrets/key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout':10
    })
    printer_ref = db.reference("Printers/"+main_data["printer_id"])
    printer_ref.child("states").child("internet").set(True)
    snmp=printer_ref.child("details").child("snmp").get()
    if(snmp==True):
        oids=printer_ref.child("details").child("oids").get()
    def setup_dns_and_ip():
        def get_ip_from_mdns(hostname):
            trying=0
            while 1:
                trying+=1
                if(trying>100):
                    return None
                try:
                    ip_address = socket.gethostbyname(hostname)
                    printer_ref.child("details").child("ip").set(ip_address)
                    return ip_address
                except Exception as e:
                    print(f"Error resolving mDNS name: {e}")
                    time.sleep(1)
        dns_name=printer_ref.child("details").child("dns_name").get()
        if(dns_name==None or dns_name==""):
            ip_address = printer_ref.child("details").child("ip").get()
        else:
            ip_address = get_ip_from_mdns(dns_name+".local")
            if(ip_address==None):
                ip_address = printer_ref.child("details").child("ip").get()
                printer_ref.child("states").child("dns").set(False)
            else:
                printer_ref.child("states").child("dns").set(True)
                printer_ref.child("details").child("ip").set(ip_address)
    setup_dns_and_ip()

    key = 'rzp_live_7p3oO9G6VYLXcd'
    secret = 'aEIdELoJ4GIDf03DqpfVrGpX'
    try:
        client = razorpay.Client(auth=(key, secret))
    except Exception as e:
        logger.error('razorpay client error '+str(e))
    printer_name = printer_ref.child("details").child("name").get()
    def setup_cups():
        conn = cups.Connection()
        printers = conn.getPrinters()
        jobs = conn.getJobs()
        for job_id, job_info in jobs.items():
            conn.cancelJob(job_id)
    setup_cups()
init_setup()        


def check_network():
    global i_error
    c=0
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            c=0
            i_error=False
            time.sleep(3)
        except Exception as e:
            c+=1
            if(c==3):
                c=0
                logger.error("check network ------------------ error : "+str(e))
                i_error=True
            logger.error("check network error : "+str(p_error)+str(e))
            time.sleep(3)
server_thread1 = threading.Thread(target=check_network)
server_thread1.daemon = True
server_thread1.start()
def check_printer_connection():
    global p_error
    c=0
    while 1:
        try:
            socket.create_connection(("8.8.8.8", 53))
            c=0
            p_error=False
            time.sleep(3)
        except Exception as e:
            c+=1
            if(c==3):
                c=0
                logger.error("check printer connection ------------------ error : "+str(e))
                p_error=True
            logger.error("check printer connection error : "+str(p_error)+str(e))
            time.sleep(3)
server_thread2 = threading.Thread(target=check_printer_connection)
server_thread2.daemon = True
server_thread2.start()



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
    global p_error,ip,i_error,ip_address
    global curr_page_count
    snmpDispatcher = SnmpDispatcher()
    target = ip
    community = "public"
    oids = {
        "Printer Detailed Status": oids["oid1"],
        "printed": oids["oid2"],
        "toner level": oids["oid3"],
        "tray 1": oids["oid4"],  
        "tray 2": oids["oid5"], 
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
                refund_all()
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("toner is empty...")
            if results['tray 1'] == "0" and results['tray 2'] == "0":
                refund_all()
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
                refund_all()
                printer_ref.child("details").child("status").set("Inactive")
                printer_ref.child("details").child("status_message").set("Paper is jammed please wait for a while")
                printer_ref.child("details").child("error").set("Paper is jammed")
                paper_jammed=True
            elif "empty" in results['Printer Detailed Status'].lower() and "toner" in results['Printer Detailed Status'].lower():
                refund_all()
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
                if(dns_name==None or dns_name==""):
                    ip_address = printer_ref.child("details").child("ip").get()
                    ip=ip_address
                else:
                    ip=get_ip_from_mdns(dns_name+".local")
                    ip_address=ip
            logger.error("Unexpected Error in main loop: " + str(e))
            time.sleep(3)
def run_snmp_loop():
    asyncio.run(get_snmp_data())
server_thread = threading.Thread(target=run_snmp_loop)
server_thread.daemon = True
if(snmp):
    server_thread.start()
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def update_database(user, filename, progress_percentage):
    try:
        db.reference(f'users/{user}/printsdetails/{filename}').child("printprogress").set(progress_percentage)
    except Exception as e:
        logger.error('progress set error '+str(e))
def download_file(url, user, filename):
    retry_strategy = Retry(
        total=5, 
        backoff_factor=0.5, 
        status_forcelist=[429, 500, 502, 503, 504], 
        allowed_methods=["HEAD", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    headers = {'User-Agent': 'your-user-agent'}
    response = session.head(url, headers=headers)
    file_type = response.headers.get('Content-Type').split("/")[1]
    total_size = int(response.headers.get('content-length', 0))
    response = session.get(url, headers=headers, stream=True)
    downloaded_size = 0
    chunk_size = 8192
    previous_percentage = 0
    with open(f"printfile.{file_type}", 'wb') as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                file.write(chunk)
                downloaded_size += len(chunk)
                if total_size:
                    progress_percentage = int((downloaded_size / total_size) * 100)
                    if progress_percentage - previous_percentage >= 10:
                        executor.submit(update_database, user, filename, progress_percentage)
                        previous_percentage = progress_percentage
                else:
                    executor.submit(update_database, user, filename, 100)
    if file_type != "pdf":
        convert_to_pdf(f"printfile.{file_type}", "printfile.pdf")
    return "printfile.pdf"
def convert_to_pdf(image_path, pdf_path):
    with Image.open(image_path) as img:
        img.convert("L").save(pdf_path, "PDF",optimize=True, resolution=80.0)
def handle_print_error(user, currentfile,error="Error printing"):
    try:
        payment_id = db.reference(f'users/{user}/printsdetails/{currentfile}').child("payment_id").get()
        device_id = db.reference(f'users/{user}/details').child("device_id").get()
        web_device_id = db.reference(f'users/{user}/details').child("web_device_id").get()
        name=db.reference(f'users/{user}/printsdetails/{currentfile}').child("name").get()
        amount_to_refund = int(db.reference(f'users/{user}/printsdetails/{currentfile}').child("cost").get() * 100)
        try:
            db.reference(f'users/{user}/printsdetails/{currentfile}').child("status").set(error+", money will be refunded")
            refund = client.payment.refund(payment_id, {
                "amount": str(amount_to_refund),
                "speed": "normal"
            })
            refund_success = True
        except Exception as e:
            logger.error(f"Error initiating specific refund: {e}")
            refund_success = False
        if not refund_success:
            try:
                refund = client.payment.refund(payment_id)
                refund_success = True
            except Exception as e:
                logger.error(f"Error initiating full refund: {e}")
                refund_success = False
        if refund_success:
            send_high_priority_notification(web_device_id, title="Refund initiated Rs." + str(amount_to_refund/100), body="Refund for file " + currentfile + " initiated due to"+error, data={"file": currentfile})
            send_high_priority_notification(device_id, title="Refund initiated Rs." + str(amount_to_refund/100), body="Refund for file " + currentfile + " initiated due to"+error, data={"file": currentfile})
            db.reference(f'users/{user}/printsdetails/{currentfile}').child("status").set(error+", money refunded, refund id: " + str(refund.get("id", "")))
            db.reference(f'users/{user}/printsdetails/{currentfile}').child("refund_id").set(str(refund.get("id", "")))
            logger.info("Refund initiated successfully.")
        else:
            db.reference(f'users/{user}/printsdetails/{currentfile}').child("status").set(error+", refund in progress")
            db.reference("refund_fails").child(payment_id).child("file").set(currentfile)
            db.reference("refund_fails").child(payment_id).child("error").set(error)
            db.reference("refund_fails").child(payment_id).child("user").set(user)
            logger.error("Failed to initiate refund after multiple attempts")
    except Exception as e:
        logger.error('error handle refund '+str(e))
def refund_all(error="Error printing"):
    try:
        ref=db.reference(f"Printers/{main_data['printer_id']}/printstodo")
        data1=ref.get()
        if data1 is None:
            return
        for key,value in data1.items():
            print(key,value)
            user=value["user"]
            files=value["files"].split(",")
            printing=value.get("printing",1)
            done_printing=value.get("done_printing",0)
            for file in files[done_printing:]:
                print(file)
                handle_print_error(user, file,error)
        ref.delete()
    except Exception as e:
        logger.error('refund failed '+str(e))
        ref.delete()
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
def print_file_without_snmp(user, file):
    file_data = db.reference(f'users/{user}/printsdetails/{file}').get()
    if file_data["count"]==0:
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Done")
        return 0,0
    try:
        filename = download_file(file_data["link"], user, file)
        db.reference(f'users/{user}/printsdetails/{file}').child("states").child("download").set(True)
    except Exception as e:
        db.reference(f'users/{user}/printsdetails/{file}').child("states").child("download").set(False)
        logger.error(f"Error downloading file: {e}")
        raise Exception("Error downloading file")
    options=db.reference(f'users/{user}/printsdetails/{file}').child("properties").get()
    options["copies"]= str(file_data["count"])
    timestamp = str(int(time.time()))
    try:
        print_job_id = conn.printFile(printer_name, os.path.abspath(filename), timestamp, options)
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("printing...")
        time_c=time.time()
        while time.time()-time_c<120:
            state_description, state_reasons = get_print_job_state(conn, print_job_id)
            if state_description is None and state_reasons is None:
                return 0,print_job_id
            if state_reasons:
                return 1,print_job_id
            if state_description == "Completed":
                logger.info(f"Print job ID: {print_job_id}")
                return 1,print_job_id
            elif state_description in ["Canceled", "Aborted", "Stopped"]:
                db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
                logger.info('Error at printer')
                for job_id, job_info in jobs.items():
                    conn.cancelJob(job_id)
                return 0,print_job_id
            time.sleep(0.5)
        return 0,print_job_id
    except Exception as e:
        try:
            db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
        except Exception as e:
            logger.error(f"Error at set status: {e}")
        logger.error(f"Error at printer: {e}")
        raise Exception("Error at printer")

def print_file_with_snmp(user, file):
    file_data = db.reference(f'users/{user}/printsdetails/{file}').get()
    if file_data["count"]==0:
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Done")
        return 0,0
    try:
        filename = download_file(file_data["link"], user, file)
        db.reference(f'users/{user}/printsdetails/{file}').child("states").child("download").set(True)
    except Exception as e:
        db.reference(f'users/{user}/printsdetails/{file}').child("states").child("download").set(False)
        logger.error(f"Error downloading file: {e}")
        raise Exception("Error downloading file")
    options=db.reference(f'users/{user}/printsdetails/{file}').child("properties").get()
    options["copies"]= str(file_data["count"])
    timestamp = str(int(time.time()))
    try:
        print_job_id = conn.printFile(printer_name, os.path.abspath(filename), timestamp, options)
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("printing...")
        return 1,print_job_id
    except Exception as e:
        try:
            db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
        except Exception as e:
            logger.error(f"Error at set status: {e}")
        logger.error(f"Error at printer: {e}")
        raise Exception("Error at printer")

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
                if(snmp):
                    on_value_change_without_snmp(first_key,data[first_key])
                else:
                    on_value_change_with_snmp(first_key,data[first_key])



def on_value_change_with_snmp(event_key,data):
    global p_error,i_error
    try:
        if event_key:
            user_ref=db.reference(f'users/{user}/printsdetails/{files[i]}')
            data = db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').get()
            if data:
                init_page_count = curr_page_count
                pc = 0
                files = data["files"]
                f = files
                files = files.split(",")
                user = data["user"]
                printing_pages = []
                job_ids = []
                i=0
                totalcost=0
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
                                totalcost+=db.reference(f'users/{user}/printsdetails/{file}').child('cost').get()
                                p,job_id = print_file_with_snmp(user, file) 
                                if p:
                                    up_c = int(db.reference(f'users/{user}/printsdetails/{file}/properties').child('count_per_page').get().split(" ")[0])
                                    total_pc = math.ceil(db.reference(f'users/{user}/printsdetails/{file}').child('pagecount').get() / up_c) * db.reference(f'users/{user}/printsdetails/{file}').child('count').get()
                                    pc += total_pc
                                    job_ids.append(job_id)
                                    printing_pages.append(pc)
                                else:
                                    printing_pages.append(pc)
                                    job_ids.append(job_id)
                            except Exception as e:
                                printing_pages.append(pc)
                                job_ids.append(0)
                                logger.error(f"Error at printing {file}: {e}")
                                handle_print_error(user, file)
                            count += 1
                        logger.info("Sent to printer")
                    except Exception as e:
                        logger.error(f"Error in print thread: {e}")
                t1 = threading.Thread(target=l1)
                t1.daemon = True
                t1.start()
                printed_sum=0
                times=[0 for i in range(len(files))]
                while True:
                    times[i] += 1
                    if times[i] > 60:
                        state_description, state_reasons = get_print_job_state(conn, job_ids[i])
                        logger.info(f"Print Job State: {state_description}")
                        if state_reasons:
                            logger.info(f"State Reasons: {state_reasons}")
                        if state_description == "Completed":
                            db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("now printing...")
                            logger.info(f"Print job ID: {job_ids[i]}")
                        elif state_description in ["Canceled", "Aborted", "Stopped"]:
                            logger.info("Print job did not complete successfully.")
                            db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("Error at printer")
                            logger.info('Error at printer')
                            handle_print_error(user, files[i],"Error at printer taking too long try again")
                            conn.cancelJob(job_ids[i])
                            i+=1
                            init_page_count-=printing_pages[i]
                            continue
                        else:
                            if(times[i]>120):
                                logger.info("Print job did not complete successfully.")
                                db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("Error at printer")
                                logger.info('Error at printer')
                                handle_print_error(user, files[i],"Error at printer taking too long try again")
                                i+=1
                                conn.cancelJob(job_ids[i])
                                init_page_count-=printing_pages[i]
                                continue
                    pages_printed = int(curr_page_count) - int(init_page_count)
                    if(len(printing_pages)<=i):
                        time.sleep(1)
                        continue
                    db.reference(f'users/{user}/printsdetails/{files[i]}').child("printed").set(f"{pages_printed-printed_sum}/{printing_pages[i]-printed_sum}")
                    if pages_printed >= printing_pages[i]:
                        printed_sum=printing_pages[i]
                        db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("Done printing")
                        db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("done_printing").set(i+1)
                        i = i + 1
                        if i == len(files):
                            db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').delete()
                            db.reference(f'Printers/{main_data["printer_id"]}/printeddetails').child(datetime.datetime.now().strftime("%d-%m-%y")).push().set({"user":user,"files":files,"status":"Done","time":datetime.datetime.now(),"name":user_ref.child("name").get(),"totalcost":totalcost})
                            break
                    if p_error or i_error:
                        refund_all(error="Error at printer taking too long try again")
                        db.reference(f'Printers/{main_data["printer_id"]}/printeddetails').child(datetime.datetime.now().strftime("%d-%m-%y")).push().set({"user":user,"files":files,"status":"Error","time":datetime.datetime.now(),"name":user_ref.child("name").get(),"totalcost":totalcost})
                        logger.error('Error at page count diff p_error')
                        break
                    time.sleep(1)
    except Exception as e:
        time.sleep(3)
        logger.error('error value listner'+str(e))
        t1.terminate()
        try:
            db.reference(f'Printers/{main_data["printer_id"]}/printeddetails').child(datetime.datetime.now().strftime("%d-%m-%y")).push().set({"user":user,"files":files,"status":"Error","time":datetime.datetime.now(),"name":user_ref.child("name").get()})
            db.reference(f'Printers/123456/printstodo/{event_key}').delete()
        except Exception as e:
            raise Exception("Error at listner")




def on_value_change_without_snmp(event_key,data):
    try:
        if event_key:
            user_ref=db.reference(f'users/{user}/printsdetails')
            data = db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').get()
            if data:
                files = data["files"]
                f = files
                files = files.split(",")
                user = data["user"]
                i=0
                totalcost=0
                count=1
                for file in files:
                    try:
                        db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("printing").set(count)
                        db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("done_printing").set(i)
                        db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("user").set(user)
                        db.reference(f'Printers/{main_data["printer_id"]}/printstodo/{event_key}').child("files").set(f)
                        logger.info(f"Printing: {file}")
                        totalcost+=db.reference(f'users/{user}/printsdetails/{file}').child('cost').get()
                        p,job_id = print_file_without_snmp(user, file) 
                        if p:
                            user_ref.child(file).child("states").child("print").set(True)
                            user_ref.child(file).child("status").set("Done Printing")
                        else:
                            handle_print_error(user, file)
                            user_ref.child(file).child("states").child("print").set(False)
                            user_ref.child(file).child("status").set("Error Printing")
                    except Exception as e:
                        user_ref.child(file).child("states").child("print").set(False)
                        logger.error(f"Error at printing {file}: {e}")
                        handle_print_error(user, file,"Error Printing")
                    i+=1
                    count += 1
    except Exception as e:
        logger.error(f"Error in on_value_change1: {e}")
        raise Exception("error in on_value_change1")
def main():
    ref = db.reference(f'Printers/{main_data["printer_id"]}/printstodo')
    while 1:
        try:
            printer_connection=False
            #ping test
            #lpstat -t
            #http client
            #pyipp module
            if printer_connection:
                db.reference(f'Printers/{main_data["printer_id"]}/states').child("printer_connection").set(True)
                listner=ref.listen(on_value_change)
                while 1:
                    if(i_error or p_error):
                        logger.error('error i_error or p_error'+str(i_error)+str(p_error))
                        listner.close()
                        raise Exception("i_error or p_error")
                    time.sleep(1)
            else:
                db.reference(f'Printers/{main_data["printer_id"]}/states').child("printer_connection").set(False)
        except Exception as e:
            refund_all()
            try:
                db.reference(f'Printers/{main_data["printer_id"]}/states').child("printer_connection").set(False)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
            logger.error(f"Error in main loop: {e}")
        time.sleep(2)



if __name__ == "__main__":
    main()