"""
Printer Management System

This application manages print jobs through Firebase, monitors printer status via SNMP,
and provides a reliable printing service with error handling and status reporting.
"""

import asyncio
import json
import logging
import math
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import cups
import firebase_admin
import PyPDF2
import razorpay
import requests
from firebase_admin import credentials, db, messaging
from PIL import Image
from pysnmp.hlapi.v1arch.asyncio import *
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib3.util.retry import Retry


class PrinterManagementSystem:
    def __init__(self):
        self.setup_logging()
        self.cwd = os.getcwd()
        self.main_data = self.read_json_file(f"{self.cwd}/../secrets/details.json")
        self.main_data["printer_id"] = self.main_data["code"]
        
        # State variables
        self.p_error = True  # Printer error flag
        self.i_error = True  # Internet error flag
        self.ip_address = ""
        self.dns_name = ""
        self.printer_name = ""
        self.ip = ""
        self.printer_ref = None
        self.curr_page_count = 0
        self.pr = ""  # Used in print job tracking
        
        # Initialize connections
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.initialize_firebase()
        self.initialize_cups()
        
        # Start monitoring threads
        self.start_monitoring_threads()
    
    def setup_logging(self):
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def read_json_file(self, file_path):
        """Read JSON data from file."""
        with open(file_path, 'r') as file:
            return json.load(file)
    
    def initialize_firebase(self):
        """Initialize Firebase connection and credentials."""
        cred = credentials.Certificate(f"{self.cwd}/secrets/key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
            'httpTimeout': 10
        })
        asyncio.run(self.init_firebase_refs())
    
    async def init_firebase_refs(self):
        """Initialize Firebase references and retrieve printer information."""
        while True:
            try:
                self.printer_ref = db.reference(f"Printers/{self.main_data['printer_id']}")
                
                # Set initial status
                self.printer_ref.child("details").child("status_message").set("Fetching IP address")
                self.printer_ref.child("details").child("status").set("Inactive")
                
                # Get printer configuration
                self.dns_name = self.printer_ref.child("details").child("dns_name").get()
                self.printer_name = self.printer_ref.child("details").child("name").get()
                
                # Resolve IP address
                if not self.dns_name:
                    self.ip_address = self.printer_ref.child("details").child("ip").get()
                else:
                    self.ip_address = await self.get_ip_from_mdns(f"{self.dns_name}.local")
                
                self.ip = self.ip_address
                self.printer_ref.child("details").child("status_message").set("Fetched IP address")
                self.i_error = False
                break
            except Exception as e:
                self.i_error = True
                self.logger.error(f'Failed to initialize Firebase: {e}')
                await asyncio.sleep(3)
    
    async def get_ip_from_mdns(self, hostname):
        """Resolve IP address from mDNS hostname."""
        while True:
            try:
                ip_address = socket.gethostbyname(hostname)
                if self.printer_ref:
                    self.printer_ref.child("details").child("ip").set(ip_address)
                return ip_address
            except Exception as e:
                self.logger.error(f"Error resolving mDNS name: {e}")
                self.p_error = True
                await asyncio.sleep(1)
    
    def initialize_cups(self):
        """Initialize CUPS connection and cancel pending jobs."""
        self.conn = cups.Connection()
        self.printers = self.conn.getPrinters()
        
        # Cancel any pending print jobs
        jobs = self.conn.getJobs()
        for job_id in jobs:
            self.conn.cancelJob(job_id)
            
        # Log existing jobs
        for job_id, job_info in jobs.items():
            job_state = job_info.get("job-state", None)
            job_state_reasons = job_info.get("job-state-reasons", "")
            if job_state == 3:  # Pending state
                self.logger.info(
                    f"Job ID: {job_id}, Title: {job_info['job-name']}, "
                    f"User: {job_info['job-originating-user-name']}, "
                    f"State: Pending, Reason: {job_state_reasons}"
                )
    
    def start_monitoring_threads(self):
        """Start monitoring threads for network, SNMP, and print jobs."""
        # Network monitoring thread
        network_thread = threading.Thread(target=self.check_network)
        network_thread.daemon = True
        network_thread.start()
        
        # SNMP monitoring thread
        snmp_thread = threading.Thread(target=self.run_snmp_loop)
        snmp_thread.daemon = True
        snmp_thread.start()
        
        # Status reporting thread (optional)
        status_thread = threading.Thread(target=self.check_i_error_p_error)
        status_thread.daemon = True
        status_thread.start()
    
    def check_network(self):
        """Monitor internet connectivity."""
        connection_failures = 0
        while True:
            try:
                socket.create_connection(("8.8.8.8", 53))
                connection_failures = 0
                self.i_error = False
                time.sleep(5)
            except Exception as e:
                connection_failures += 1
                if connection_failures >= 3:
                    connection_failures = 0
                    self.logger.error(f"Network connectivity error: {e}")
                    self.i_error = True
                time.sleep(5)
    
    def check_i_error_p_error(self):
        """Report printer and internet status to web interface."""
        while True:
            try:
                if not (self.i_error or self.p_error):
                    requests.post(
                        "http://localhost:5000/update_data", 
                        json={"message": "internet connected"}
                    )
                else:
                    requests.post(
                        "http://localhost:5000/update_data", 
                        json={"message": "no internet"}
                    )
                time.sleep(3)
            except Exception:
                self.logger.error("Error sending status update to web interface")
    
    def run_snmp_loop(self):
        """Run the SNMP data collection loop."""
        asyncio.run(self.get_snmp_data())
    
    async def get_snmp_data(self):
        """Collect SNMP data from printer."""
        snmp_dispatcher = SnmpDispatcher()
        
        # SNMP OIDs for printer information
        oids = {
            "Printer Detailed Status": "1.3.6.1.2.1.43.16.5.1.2.1.1",
            "printed": "1.3.6.1.2.1.43.10.2.1.4.1.1",
            "toner level": "1.3.6.1.2.1.43.11.1.1.9.1.1",
            "tray 1": "1.3.6.1.2.1.43.8.2.1.10.1.2",  
            "tray 2": "1.3.6.1.2.1.43.8.2.1.10.1.3", 
        }
        
        # Status flags
        conn_error = False
        no_papers = False
        paper_jammed = False
        no_toner = False
        error_count = 0
        
        while True:
            try:
                results = {}
                for key, oid in oids.items():
                    result = await self.query_snmp_data(snmp_dispatcher, oid, self.ip)
                    if result is not None:
                        results[key] = result
                        self.p_error = False
                    else:
                        self.p_error = True
                        self.logger.warning(f"Failed to retrieve data for {key}")
                        results[key] = "Error"
                
                # Update database with printer status
                if results['printed'] != "Error":
                    self.update_printer_status(results)
                
                # Check for printer issues
                await self.check_printer_issues(results, conn_error, no_papers, paper_jammed, no_toner)
                
                # Reset error count
                error_count = 0
                
                # Update connection status if needed
                if conn_error:
                    conn_error = False
                    status_message = self.printer_ref.child("details").child("status_message").get()
                    if status_message == "printer is restarting network issue at fetching data":
                        self.printer_ref.child("details").child("status").set("Active")
                        self.printer_ref.child("details").child("status_message").set("Printer is Active")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                error_count += 1
                if error_count > 5:
                    self.p_error = True
                    error_count = 0
                    
                    try:
                        self.printer_ref.child("details").child("status").set("Inactive")
                        self.printer_ref.child("details").child("status_message").set(
                            "printer is restarting network issue at fetching data"
                        )
                        conn_error = True
                    except Exception as e1:
                        self.i_error = True
                        self.logger.error(f"Failed to update printer status: {e1}")
                    
                    # Re-resolve IP address
                    if not self.dns_name:
                        self.ip_address = self.printer_ref.child("details").child("ip").get()
                        self.ip = self.ip_address
                    else:
                        self.ip = await self.get_ip_from_mdns(f"{self.dns_name}.local")
                        self.ip_address = self.ip
                
                self.logger.error(f"Unexpected error in SNMP loop: {e}")
                await asyncio.sleep(3)
    
    def update_printer_status(self, results):
        """Update printer status in Firebase database."""
        self.printer_ref.child("details").child("pages_printed").set(results['printed'])
        self.curr_page_count = results['printed']
        self.printer_ref.child("details").child("tray_1").set(results['tray 1'])
        self.printer_ref.child("details").child("tray_2").set(results['tray 2'])
        self.printer_ref.child("details").child("toner_level").set(results['toner level'])
    
    async def check_printer_issues(self, results, conn_error, no_papers, paper_jammed, no_toner):
        """Check for printer issues based on SNMP data."""
        # Check toner status
        if 'toner is out (black).' in results['Printer Detailed Status']:
            self.printer_ref.child("details").child("status").set("Inactive")
            self.printer_ref.child("details").child("status_message").set("toner is empty...")
        
        # Check paper status
        if results['tray 1'] == "0" and results['tray 2'] == "0":
            self.printer_ref.child("details").child("status").set("Inactive")
            self.printer_ref.child("details").child("status_message").set("Printer is empty please wait for a while")
            no_papers = True
        
        # Check if paper issue is resolved
        if no_papers:
            if results['tray 1'] != "0" or results['tray 2'] != "0":
                status_message = self.printer_ref.child("details").child("status_message").get()
                if status_message == "Printer is empty please wait for a while":
                    self.printer_ref.child("details").child("status").set("Active")
                    self.printer_ref.child("details").child("status_message").set("Printer is Active")
                no_papers = False
        
        # Check if paper jam is resolved
        if paper_jammed:
            if "paper jam" not in results['Printer Detailed Status'].lower():
                status_message = self.printer_ref.child("details").child("status_message").get()
                if status_message == "Paper is jammed please wait for a while":
                    self.printer_ref.child("details").child("status").set("Active")
                    self.printer_ref.child("details").child("status_message").set("Printer is Active")
                    paper_jammed = False
        
        # Check if toner issue is resolved
        if no_toner:
            condition = "empty" in results['Printer Detailed Status'].lower() and "toner" in results['Printer Detailed Status'].lower()
            if not condition:
                status_message = self.printer_ref.child("details").child("status_message").get()
                if status_message == "Toner is empty takes 10-100mins to refill":
                    self.printer_ref.child("details").child("status").set("Active")
                    self.printer_ref.child("details").child("status_message").set("Printer is Active")
                    no_toner = False
        
        # Check for new paper jam
        if "paper jam" in results['Printer Detailed Status'].lower():
            self.printer_ref.child("details").child("status").set("Inactive")
            self.printer_ref.child("details").child("status_message").set("Paper is jammed please wait for a while")
            self.printer_ref.child("details").child("error").set("Paper is jammed")
            paper_jammed = True
        
        # Check for new toner issue
        elif "empty" in results['Printer Detailed Status'].lower() and "toner" in results['Printer Detailed Status'].lower():
            self.printer_ref.child("details").child("status").set("Inactive")
            self.printer_ref.child("details").child("status_message").set("Toner is empty takes 10-100mins to refill")
            self.printer_ref.child("details").child("error").set("Toner is empty")
            no_toner = True
        else:
            self.printer_ref.child("details").child("error").set(results['Printer Detailed Status'])
    
    async def query_snmp_data(self, snmp_dispatcher, oid, ip):
        """Query SNMP data from the printer."""
        try:
            async def snmp_query():
                return await get_cmd(
                    snmp_dispatcher,
                    CommunityData("public", mpModel=0),
                    await UdpTransportTarget.create((ip, 161), timeout=3, retries=2),
                    ObjectType(ObjectIdentity(oid))
                )

            # Use asyncio.wait_for to enforce timeout
            try:
                iterator = await asyncio.wait_for(snmp_query(), timeout=5)
            except asyncio.TimeoutError:
                raise Exception("SNMP query timed out")

            error_indication, error_status, error_index, var_binds = iterator

            if error_indication:
                self.logger.error(f"SNMP Error: {error_indication}")
                raise Exception("Error querying SNMP data")
            elif error_status:
                self.logger.error(f"Error Status: {error_status.prettyPrint()} at {error_index}")
                raise Exception("Error querying SNMP data")
            else:
                return var_binds[0][1].prettyPrint()
        except Exception as e:
            self.logger.error(f"SNMP query error: {e}")
            raise
    
    def get_print_job_state(self, job_id):
        """Get the state of a print job."""
        try:
            job_attributes = self.conn.getJobAttributes(job_id)
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
            self.logger.error(f"Failed to get job state: {e}")
            return None, None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def update_database(self, user, filename, progress_percentage):
        """Update print progress in Firebase database."""
        try:
            db.reference(f'users/{user}/printsdetails/{filename}').child("printprogress").set(progress_percentage)
        except Exception as e:
            self.logger.error(f'Progress update error: {e}')
            raise
    
    def convert_to_pdf(self, image_path, pdf_path):
        """Convert an image to PDF format."""
        with Image.open(image_path) as img:
            img.convert("L").save(pdf_path, "PDF", optimize=True, resolution=80.0)
    
    def send_high_priority_notification(self, token, title="", body="", data={}):
        """Send high priority notification via Firebase."""
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
            self.logger.info(f'Successfully sent message: {response}')
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
    
    def print_file(self, user, file):
        """Print a file from Firebase storage."""
        file_data = db.reference(f'users/{user}/printsdetails/{file}').get()
        
        # Check if print count is valid
        if file_data["count"] == 0:
            db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Done")
            return 0, None
        
        # Update printing status
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Downloading file...")
        db.reference(f'users/{user}/printsdetails/{file}').child("printprogress").set(0)
        
        try:
            # Prepare file path
            filename = f"{self.cwd}/files/{user}/{file_data['name'].replace(' ', '_')}"
            self.logger.info(f"Printing file: {filename}")
        except Exception as e:
            db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error downloading file")
            self.logger.error(f"Error preparing file for printing: {e}")
            raise Exception("Error downloading file")
        
        self.logger.info("File downloaded")
        db.reference(f'users/{user}/printsdetails/{file}').child("status").set("File downloaded, starting printing...")
        
        # Get printing options
        options = file_data["properties"]
        timestamp = str(int(time.time()))
        
        try:
            # Send file to printer
            print_job_id = self.conn.printFile(self.printer_name, filename, timestamp, options)
            db.reference(f'users/{user}/printsdetails/{file}').child("status").set("printing...")
            
            timeout_counter = 0
            
            # Monitor printing status
            while True:
                timeout_counter += 1
                state_description, state_reasons = self.get_print_job_state(print_job_id)
                
                # Log job state
                self.logger.info(f"Print Job State: {state_description}")
                if state_reasons:
                    self.logger.info(f"State Reasons: {state_reasons}")
                    return 1, print_job_id
                
                # Handle job completion
                if state_description == "Completed":
                    db.reference(f'users/{user}/printsdetails/{file}').child("status").set("printing...")
                    self.logger.info("Print job completed. Status set to 'Done'.")
                    self.logger.info(f"Print job ID: {print_job_id}")
                    return 1, print_job_id
                
                # Handle job failure
                elif state_description in ["Canceled", "Aborted", "Stopped"]:
                    self.logger.info("Print job did not complete successfully.")
                    db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
                    self.logger.info('Error at printer')
                    return 0, print_job_id
                
                # Check for timeout
                if timeout_counter > 200:
                    self.conn.cancelJob(print_job_id)
                    return 0, print_job_id
                
                time.sleep(0.5)
                
        except Exception as e:
            try:
                db.reference(f'users/{user}/printsdetails/{file}').child("status").set("Error at printer")
            except Exception as db_error:
                self.logger.error(f"Error updating status: {db_error}")
            
            self.logger.error(f"Printing error: {e}")
            raise Exception("Error at printer")
        
        self.logger.info(f"Print job ID: {print_job_id}")
        return 1, print_job_id
    
    def on_value_change(self, event):
        """Handle changes in the print queue."""
        data = db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo').get()
        if data is not None:
            keys = list(data.keys())
            if keys:
                first_key = keys[0]
                if self.pr != first_key:
                    self.pr = first_key 
                    self.logger.info(f"New print job: {first_key}: {data[first_key]}")
                    self.process_print_job(first_key, data[first_key])
    
    def process_print_job(self, job_key, job_data):
        """Process a print job."""
        try:
            # Double-check the job data
            job_data = db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo/{job_key}').get()
            
            if job_data:
                # Get initial page count
                init_page_count = self.curr_page_count
                printed_count = 0
                
                # Parse file list
                files_string = job_data["files"]
                files = files_string.split(",")
                user = job_data["user"]
                
                # Track printing progress
                printing_pages = []
                job_ids = []
                current_file_index = 0
                
                # Create printing thread
                def print_thread_function():
                    nonlocal printed_count, printing_pages
                    count = 1
                    try:
                        for file in files:
                            # Update job status
                            self.update_job_status(job_key, count, current_file_index, user, files_string)
                            
                            self.logger.info(f"Printing: {file}")
                            try:
                                # Print the file
                                success, job_id = self.print_file(user, file) 
                                if success:
                                    # Calculate pages
                                    up_count = int(db.reference(f'users/{user}/printsdetails/{file}/properties').child('count_per_page').get().split(" ")[0])
                                    page_count = db.reference(f'users/{user}/printsdetails/{file}').child('pagecount').get()
                                    copies = db.reference(f'users/{user}/printsdetails/{file}').child('count').get()
                                    
                                    total_pages = math.ceil(page_count / up_count) * copies
                                    printed_count += total_pages
                                    
                                    job_ids.append(job_id)
                                    printing_pages.append(printed_count)
                                else:
                                    printing_pages.append(printed_count)
                                    job_ids.append(job_id)
                            except Exception as e:
                                printing_pages.append(printed_count)
                                job_ids.append(0)
                                self.logger.error(f"Error printing {file}: {e}")
                            count += 1
                        self.logger.info("All files sent to printer")
                    except Exception as e:
                        self.logger.error(f"Error in print thread: {e}")
                
                # Start printing thread
                print_thread = threading.Thread(target=print_thread_function)
                print_thread.daemon = True
                print_thread.start()
                
                # Monitor printing progress
                printed_sum = 0
                timeouts = [0] * len(files)
                
                while True:
                    # Update timeout counter
                    timeouts[current_file_index] += 1
                    
                    # Check for timeout
                    if timeouts[current_file_index] > 60:
                        state_description, state_reasons = self.get_print_job_state(job_ids[current_file_index])
                        self.logger.info(f"Print Job State: {state_description}")
                        
                        if state_reasons:
                            self.logger.info(f"State Reasons: {state_reasons}")
                        
                        # Handle job completion
                        if state_description == "Completed":
                            db.reference(f'users/{user}/printsdetails/{files[current_file_index]}').child("status").set("now printing...")
                            self.logger.info("Print job completed. Status set to 'now printing...'.")
                            self.logger.info(f"Print job ID: {job_ids[current_file_index]}")
                        
                        # Handle job failure
                        elif state_description in ["Canceled", "Aborted", "Stopped"]:
                            self.logger.info("Print job did not complete successfully.")
                            db.reference(f'users/{user}/printsdetails/{files[current_file_index]}').child("status").set("Error at printer")
                            self.logger.info('Error at printer')
                            self.conn.cancelJob(job_ids[current_file_index])
                            current_file_index += 1
                            init_page_count -= printing_pages[current_file_index]
                            continue
                        
                        # Handle excessive timeout
                        else:
                            if timeouts[current_file_index] > 120:
                                self.logger.info("Print job timed out.")
                                db.reference(f'users/{user}/printsdetails/{files[current_file_index]}').child("status").set("Error at printer")
                                self.logger.info('Error at printer (timeout)')
                                current_file_index += 1
                                self.conn.cancelJob(job_ids[current_file_index])
                                init_page_count -= printing_pages[current_file_index]
                                continue
                    
                    # Check if printing information is available
                    if len(printing_pages) <= current_file_index:
                        time.sleep(1)
                        continue
                    
                    # Calculate and update progress
                    pages_printed = int(self.curr_page_count) - int(init_page_count)
                    progress_display = f"{pages_printed-printed_sum}/{printing_pages[current_file_index]-printed_sum}"
                    db.reference(f'users/{user}/printsdetails/{files[current_file_index]}').child("printed").set(progress_display)
                    
                    # Check if current file is complete
                    if pages_printed >= printing_pages[current_file_index]:
                        printed_sum = printing_pages[current_file_index]
                        db.reference(f'users/{user}/printsdetails/{files[current_file_index]}').child("status").set("Done printing")
                        db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo/{job_key}').child("done_printing").set(current_file_index + 1)
                        
                        current_file_index += 1
                        if current_file_index == len(files):
                            # All files printed, mark job as complete
                            db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo/{job_key}').delete()
                            self.record_completed_job(user, files)
                            break
                    
                    # Check for printer or internet errors
                    if self.p_error or self.i_error:
                        self.record_completed_job(user, files)
                        self.logger.error('Error during printing: printer or internet connection issue')
                        break
                    
                    time.sleep(1)
            
        except Exception as e:
            self.logger.error(f'Error processing print job: {e}')
            time.sleep(3)
            
            try:
                print_thread.terminate()  # This isn't standard for Python threads
            except Exception:
                pass
                
            try:
                db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo/{job_key}').delete()
            except Exception:
                self.logger.error("Error cleaning up print job")
    
    def update_job_status(self, job_key, count, done_printing, user, files):
        """Update job status in Firebase."""
        job_ref = db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo/{job_key}')
        job_ref.child("printing").set(count)
        job_ref.child("done_printing").set(done_printing)
        job_ref.child("user").set(user)
        job_ref.child("files").set(files)
    
    def record_completed_job(self, user, files):
        """Record completed job in database."""
        import datetime  # Import at function level since it's only used here
        
        try:
            user_ref = db.reference(f'users/{user}')
            user_name = user_ref.child("name").get()
            
            # Get total cost (this should be calculated properly based on your business logic)
            total_cost = self.calculate_total_cost(user, files)
            
            # Record in printed details
            date_str = datetime.datetime.now().strftime("%d-%m-%y")
            db.reference(f'Printers/{self.main_data["printer_id"]}/printeddetails').child(date_str).push().set({
                "user": user,
                "files": files,
                "status": "Done",
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "name": user_name,
                "totalcost": total_cost
            })
        except Exception as e:
            self.logger.error(f"Error recording completed job: {e}")
    
    def calculate_total_cost(self, user, files):
        """Calculate the total cost of printing."""
        # This is a placeholder - implement your actual cost calculation logic
        try:
            total_cost = 0
            for file in files:
                file_data = db.reference(f'users/{user}/printsdetails/{file}').get()
                # Example calculation (replace with your actual pricing model)
                page_count = file_data.get('pagecount', 0)
                copies = file_data.get('count', 1)
                price_per_page = 1.0  # Example price
                total_cost += page_count * copies * price_per_page
            return total_cost
        except Exception as e:
            self.logger.error(f"Error calculating cost: {e}")
            return 0
    
    async def run_server(self):
        """Main server loop to monitor printer status and process jobs."""
        listeners = []
        ref = db.reference(f'Printers/{self.main_data["printer_id"]}/printstodo')
        
        while True:
            try:
                # Test printer connection
                response = requests.get(f"http://{self.ip_address}:8000", timeout=5)
                
                # Set initial status during connection attempt
                self.printer_ref.child("details").child("status").set("InActive")
                self.printer_ref.child("details").child("status_message").set("trying to connect..")
                self.logger.info(f"Trying to connect... Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Clean up old listeners
                    for listener in listeners:
                        listener.close()
                    listeners = []
                    
                    # Set printer as active
                    self.printer_ref.child("details").child("status").set("Active")
                    self.printer_ref.child("details").child("status_message").set("Printer is Active")
                    self.logger.info("Connected to printer")
                    self.i_error = False
                    
                    # Start listening for new print jobs
                    listener = ref.listen(self.on_value_change)
                    listeners.append(listener)
                    
                    # Monitor listeners and connection status
                    while True:
                        for listener in listeners:
                            if not listener._thread.is_alive():
                                raise Exception("Listener has died")
                        
                        if self.i_error or self.p_error:
                            self.logger.error(f"Connection issues detected: i_error={self.i_error}, p_error={self.p_error}")
                            for listener in listeners:
                                listener.close()
                            listeners = []
                            raise Exception("Internet or printer error")
                        
                        await asyncio.sleep(3)
                else:
                    # Clean up listeners if connection failed
                    for listener in listeners:
                        listener.close()
                    listeners = []
                    
                    self.logger.info("Connecting to printer...")
                    self.printer_ref.child("details").child("status_message").set("connecting...")
                    await asyncio.sleep(5)
                    continue
            except Exception as e:
                self.logger.error(f"Error in server loop: {e}")
                
                if self.i_error or self.p_error:
                    self.logger.error(f"Connection issue in main loop: {e}")
                    await asyncio.sleep(3)
                    
                    for listener in listeners:
                        listener.close()
                    listeners = []
                    continue
                
                try:
                    self.printer_ref.child("details").child("status").set("Inactive")
                    self.printer_ref.child("details").child("status_message").set("something went wrong, trying to reconnect")
                except Exception as update_error:
                    self.logger.error(f"Error updating status: {update_error}")
                
                await asyncio.sleep(5)


def main():
    """Main entry point for the application."""
    try:
        printer_system = PrinterManagementSystem()
        asyncio.run(printer_system.run_server())
    except Exception as e:
        print(f"Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        # Wait a moment before exiting to ensure logs are written
        time.sleep(1)
        exit(1)

if __name__ == "__main__":
    main()