"""
Advanced Printer Management System

This enhanced version combines the best practices from both implementations,
offering robust printer management with improved error handling,
better structure, and comprehensive monitoring capabilities.
"""

import asyncio
import datetime
import firebase_admin
from firebase_admin import credentials, db, messaging
import os
import time
import threading
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
import subprocess
import fitz
from typing import Dict, Tuple, Optional, List

# Constants and Configuration

CONFIG_FILE = "../secrets/details.json"
#FIREBASE_KEY_FILE = "secrets/key.json"
FIREBASE_KEY_FILE ="/dev/shm/atomte_secrets.json"
FIREBASE_DB_URL = "https://skilldevelopmentapp-default-rtdb.firebaseio.com/"
RAZORPAY_KEY = 'rzp_live_7p3oO9G6VYLXcd'
RAZORPAY_SECRET = 'aEIdELoJ4GIDf03DqpfVrGpX'
SNMP_COMMUNITY = "public"
SNMP_PORT = 161
SNMP_TIMEOUT = 7
SNMP_RETRIES = 3
PRINTER_CHECK_INTERVAL = 3  # seconds
MAX_PRINT_JOB_WAIT_TIME = 120  # seconds
PING_TIMEOUT = 2  # seconds
MAX_DNS_RETRIES = 100

# Global state variables
printer_error = False
internet_error = False
snmp_enabled = False
current_page_count = 0
printer_state = None
printer_ip = ""
printer_dns_name = ""
printer_ref = None
printer_name = ""
active_listeners = []
cups_connection = None
razorpay_client = None





logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


executor = ThreadPoolExecutor(max_workers=1)


class PrinterManagementError(Exception):
    """Base exception for printer management errors"""
    pass
class NetworkError(PrinterManagementError):
    """Network-related errors"""
    pass
class PrinterConnectionError(PrinterManagementError):
    """Printer connection errors"""
    pass
class PrintJobError(PrinterManagementError):
    """Print job processing errors"""
    pass

def load_config() -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(os.path.join(os.getcwd(), CONFIG_FILE), 'r') as file:
            config = json.load(file)
            config["printer_id"] = config.get("code", "")
            return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise


def initialize_firebase() -> bool:
    """Initialize Firebase connection"""
    try:
        cred = credentials.Certificate(
            # os.path.join(os.getcwd(), FIREBASE_KEY_FILE)
            os.path.join(FIREBASE_KEY_FILE)
        )
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DB_URL,
            'httpTimeout': 10
        })
        return True
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        return False


def resolve_mdns_name(hostname: str) -> Optional[str]:
    """Resolve mDNS hostname to IP address"""
    global printer_error
    
    retries = 0
    while retries < MAX_DNS_RETRIES:
        retries += 1
        try:
            ip_address = socket.gethostbyname(hostname)
            printer_ref.child("details").child("ip").set(ip_address)
            printer_error = False
            return ip_address
        except Exception as e:
            logger.error(f"Error resolving mDNS name: {e}")
            time.sleep(1)
    
    return None


def get_printer_connection_info() -> None:
    """Get printer IP address either from DNS or direct configuration"""
    global printer_error, printer_ip, printer_dns_name, printer_ref, printer_name,snmp_enabled
    
    printer_ref = db.reference(f"Printers/{config['printer_id']}")
    printer_ref.child("details").child("status_message").set("Fetching IP address")
    printer_ref.child("details").child("status").set("Inactive")
    
    printer_dns_name = printer_ref.child("details").child("dns_name").get()
    printer_name = config["pi_username"]
    snmp_enabled = printer_ref.child("details").child("snmp").get()
    
    if not printer_dns_name:
        printer_ip = printer_ref.child("details").child("ip").get()
        printer_ref.child("states").child("dns").set(False)
    else:
        printer_ip = resolve_mdns_name(f"{printer_dns_name}.local")
        if printer_ip is None:
            printer_ip = printer_ref.child("details").child("ip").get()
            printer_ref.child("states").child("dns").set(False)
        else:
            printer_ref.child("states").child("dns").set(True)
    
    printer_ref.child("details").child("status_message").set("Fetched IP address")
    printer_error = False


def initialize_razorpay() -> Optional[razorpay.Client]:
    """Initialize Razorpay client for payment processing"""
    try:
        return razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
    except Exception as e:
        logger.error(f"Razorpay client initialization failed: {e}")
        return None


def initialize_cups() -> None:
    """Initialize CUPS connection and clean up print queue"""
    global cups_connection
    
    try:
        cups_connection = cups.Connection()
        jobs = cups_connection.getJobs()
        for job_id in jobs:
            cups_connection.cancelJob(job_id)
        logger.info("Cleaned up print queue")
    except Exception as e:
        logger.error(f"Failed to initialize CUPS: {e}")
        raise


def wait_for_internet_connection() -> None:
    """Wait until internet connection is available"""
    global internet_error
    
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            internet_error = False
            break
        except OSError:
            internet_error = True
            logger.info("No internet connection. Retrying in 1 second...")
            time.sleep(1)


def initialize_system() -> None:
    """Initialize all system components"""
    global config, razorpay_client, snmp_enabled
    
    wait_for_internet_connection()
    
    if not initialize_firebase():
        raise PrinterManagementError("Failed to initialize Firebase")
    
    config = load_config()
    get_printer_connection_info()
    razorpay_client = initialize_razorpay()
    initialize_cups()
    
    # Start monitoring threads
    threading.Thread(target=monitor_network, daemon=True).start()
    # threading.Thread(target=monitor_printer_connection, daemon=True).start()
    
    if snmp_enabled:
        threading.Thread(target=run_snmp_loop, daemon=True).start()


def send_notification(token: str, title: str = "", body: str = "", data: Optional[Dict] = None) -> None:
    """Send high-priority FCM notification"""
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        android=messaging.AndroidConfig(priority="high"),
        data=data or {}
    )
    
    try:
        response = messaging.send(message)
        logger.info(f"Notification sent: {response}")
    except Exception as e:
        logger.error(f"Notification failed: {e}")


def monitor_network() -> None:
    """Continuously monitor network connectivity"""
    global internet_error
    
    error_count = 0
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=15)
            error_count = 0
            internet_error = False
            # printer_ref.child("states").child("internet").set(True)
        except Exception as e:
            error_count += 1
            if error_count >= 3:
                error_count = 0
                internet_error = True
                # printer_ref.child("states").child("internet").set(False)
                logger.error(f"Network error: {e}")
        
        time.sleep(PRINTER_CHECK_INTERVAL)


def monitor_printer_connection() -> None:
    """Continuously monitor printer connection"""
    global printer_error
    
    error_count = 0
    while True:
        try:
            if ping_printer(printer_ip):
                error_count = 0
                printer_error = False
                printer_ref.child("states").child("printer_connection").set(True)
            else:
                raise PrinterConnectionError("Ping test failed")
        except Exception as e:
            error_count += 1
            if error_count >= 3:
                error_count = 0
                printer_error = True
                printer_ref.child("states").child("printer_connection").set(False)
                logger.error(f"Printer connection error: {e}")
        
        time.sleep(PRINTER_CHECK_INTERVAL)


def ping_printer(ip_address: str) -> bool:
    """Check printer connectivity using ping"""
    try:
        response = subprocess.run(
            ["ping", "-c", "1", "-W", str(PING_TIMEOUT), ip_address],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.debug(f"Ping test result: {response.returncode}")
        return response.returncode == 0
    except Exception as e:
        logger.error(f"Ping test failed with exception: {e}")
        return False


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def update_print_progress(user: str, filename: str, progress: int) -> None:
    """Update print progress in Firebase"""
    try:
        db.reference(f'users/{user}/printsdetails/{filename}').child("printprogress").set(progress)
    except Exception as e:
        logger.error(f"Failed to update print progress: {e}")
        raise


def download_with_retry(url: str, headers: Optional[Dict] = None) -> requests.Response:
    """Create a requests session with retry logic"""
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
    return session.get(url, headers=headers or {'User-Agent': 'PrinterManagementSystem'})


def download_print_file(url: str, user: str, filename: str) -> str:
    """Download file for printing with progress tracking"""
    try:
        # Log download start
        #logger.info(f"Starting download for user '{user}', file '{filename}'")
        
        # Get file info
        response = download_with_retry(url)
        file_type = response.headers.get('Content-Type', '').split("/")[-1]
        total_size = int(response.headers.get('content-length', 0))
        
        # Download file
        response = download_with_retry(url)
        temp_file = f"printfile.{file_type}"
        downloaded_size = 0
        previous_percentage = 0
        
        with open(temp_file, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if total_size:
                        progress = int((downloaded_size / total_size) * 100)
                        if progress - previous_percentage >= 10:
                            # Log progress milestone
                            # logger.info(f"Download progress for user '{user}', file '{filename}': {progress}%")
                            executor.submit(update_print_progress, user, filename, progress)
                            previous_percentage = progress
                    else:
                        executor.submit(update_print_progress, user, filename, 100)
            else:
                executor.submit(update_print_progress, user, filename, 100)
        
        # Log download completion
        #logger.info(f"Completed download for user '{user}', file '{filename}'")
        
        # Convert to PDF if needed
        if file_type != "pdf":
            convert_to_pdf(temp_file, "printfile.pdf")
            temp_file = "printfile.pdf"
            #return "printfile.pdf"
        #return temp_file
        
        # Convert the PDF to grayscale
        grayscale_file = temp_file

        # convert_pdf_to_grayscale(temp_file, grayscale_file)

        return grayscale_file
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise PrintJobError("File download failed")


def convert_to_pdf(image_path: str, pdf_path: str) -> None:
    """Convert image file to PDF"""
    try:
        with Image.open(image_path) as img:
            img.convert("L").save(pdf_path, "PDF", optimize=True, resolution=85.0)
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        raise PrintJobError("PDF conversion failed")

def convert_pdf_to_grayscale(input_pdf_path: str, output_pdf_path: str, dpi: int = 300) -> None:
    """Convert a PDF file to a high-quality grayscale PDF."""
    try:
        start_time = time.time()  # Start timing
        doc = fitz.open(input_pdf_path)
        new_doc = fitz.open()

        # Zoom factor for resolution
        zoom = dpi / 72  # 72 is the default DPI
        matrix = fitz.Matrix(zoom, zoom)

        for page in doc:
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)
            rect = fitz.Rect(0, 0, pix.width, pix.height)
            new_page = new_doc.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(rect, pixmap=pix)

        new_doc.save(output_pdf_path, deflate=True)
        doc.close()
        new_doc.close()
        end_time = time.time()
        logger.info(f"High-quality grayscale conversion completed in {end_time - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"PDF grayscale conversion failed: {e}")
        raise PrintJobError("PDF grayscale conversion failed")

    
def handle_print_error(user: str, filename: str, error: str = "Printing error") -> None:
    """Handle print errors and process refunds"""
    try:
        user_ref = db.reference(f'users/{user}/printsdetails/{filename}')
        payment_id = user_ref.child("payment_id").get()
        device_id = db.reference(f'users/{user}/details').child("device_id").get()
        web_device_id = db.reference(f'users/{user}/details').child("web_device_id").get()
        amount = int(user_ref.child("cost").get() * 100)
        printed = user_ref.child("printed").get()
        name = user_ref.child("name").get()

        m=1
        if printed and printed != "undefined":
            try:
                done, total = map(int, printed.split("/"))
                refund = amount * (1 - done / total)
                amount = math.ceil(refund)
            except Exception as e:
                logger.error(f"Error calculating refund amount: {e}")

        # Update status
        user_ref.child("status").set(f"{error}, money will be refunded")
        user_ref.child("states").child("print").set(False)


        if payment_id=="Paid Through Wallet":
            curr_wallet_money = db.reference(f'users/{user}/wallet/balance').get()
            db.reference(f'users/{user}/wallet/balance').set(curr_wallet_money+(amount / 100))
            db.reference(f'users/{user}/wallet').child("transactions").child("credit").push({
                "amount": amount/100,
                "timestamp": int(time.time()),
                "description": f"Refund for {name} due to {error}"})
            db.reference(f'users/{user}/printsdetails/{filename}').child("status").set(f"{error}, Money added to wallet")
            refund_success = True
        else:
            refund_success = False
            try:
                refund = razorpay_client.payment.refund(payment_id, {
                    "amount": str(amount),
                    "speed": "normal"
                })
                refund_success = True
            except Exception as e:
                logger.error(f"Specific refund failed: {e}")
                try:
                    refund = razorpay_client.payment.refund(payment_id)
                    refund_success = True
                except Exception as e:
                    logger.error(f"Full refund failed: {e}")
        
        if refund_success:
            # Notify user
            notification_data = {"file": filename}
            if device_id:
                send_notification(
                    device_id,
                    f"Refund initiated Rs.{amount/100}",
                    f"Refund for {name} initiated due to {error} will be deposited in 2-3 days",
                    notification_data
                )
            if web_device_id:
                send_notification(
                    web_device_id,
                    f"Refund initiated Rs.{amount/100}",
                    f"Refund for {name} initiated due to {error} will be deposited in 2-3 days",
                    notification_data
                )                                                                                                                   
            
            # Update status
            user_ref.child("status").set(f"{error}, money refunded, refund id: {refund.get('id', '')}, will be deposited in 2-3 days")
            user_ref.child("refund_id").set(str(refund.get("id", "")))
            logger.info("Refund processed successfully")
        else:
            user_ref.child("status").set(f"{error}, refund in progress")
            db.reference("refund_fails").child(payment_id).set({
                "file": filename,
                "error": error,
                "user": user
            })
            logger.error("Refund failed after multiple attempts")
            
    except Exception as e:
        logger.error(f"Error handling print error: {e}")


def refund_all_print_jobs(error: str = "Printing error") -> None:
    """Refund all pending print jobs"""
    try:
        ref = db.reference(f"Printers/{config['printer_id']}/printstodo")
        jobs = ref.get()
        
        if not jobs:
            return
            
        for job_id, job_data in jobs.items():
            user = job_data["user"]
            files = job_data["files"].split(",")
            printing=job_data.get("done_printing",0)
            for file in files[printing:]:
                handle_print_error(user, file, error)
                
        ref.delete()
    except Exception as e:
        logger.error(f"Failed to refund all jobs: {e}")
        try:
            ref.delete()
            raise Exception("error refunding all jobs")
        except Exception as e:
            logger.error(f"Failed to delete print jobs reference: {e}")
            raise Exception("Failed to delete print jobs reference")


def get_print_job_status(job_id: int) -> Tuple[Optional[str], Optional[str]]:
    """Get status of a print job"""
    try:
        job = cups_connection.getJobAttributes(job_id)
        status_map = {
            3: "Pending",
            4: "Held",
            5: "Processing",
            6: "Stopped",
            7: "Canceled",
            8: "Aborted",
            9: "Completed"
        }
        return status_map.get(job.get("job-state"), "Unknown"), job.get("job-state-reasons", "unknown")
    except cups.IPPError as e:
        logger.error(f"Failed to get job status: {e}")
        return None, None


async def query_printer_snmp(snmpDispatcher, oid, ip):
    try:
        # First try to get the specific OID value
        async def get_specific():
            return await get_cmd(
                snmpDispatcher,
                CommunityData("public", mpModel=0),
                await UdpTransportTarget.create((ip, 161), timeout=7, retries=3),
                ObjectType(ObjectIdentity(oid))
            )

        try:
            iterator = await asyncio.wait_for(get_specific(), timeout=7)
            errorIndication, errorStatus, errorIndex, varBinds = iterator
            
            if not errorIndication and not errorStatus:
                return varBinds[0][1].prettyPrint()
                
        except Exception:
            pass  # Continue to GETNEXT if GET fails
            
        # If specific get didn't work or we want to get next values, use GETNEXT
        async def snmp_query():
            return await next_cmd(
                snmpDispatcher,
                CommunityData("public", mpModel=0),
                await UdpTransportTarget.create((ip, 161), timeout=7, retries=3),
                ObjectType(ObjectIdentity(oid))
            )
        
        all_values = []
        while True:
            try:
                iterator = await asyncio.wait_for(snmp_query(), timeout=7)
            except asyncio.TimeoutError:
                if all_values:
                    return " | ".join(all_values)
                raise Exception("SNMP query timed out")

            errorIndication, errorStatus, errorIndex, varBinds = iterator
            if errorIndication:
                if all_values:  # If we have any values, return them
                    return " | ".join(all_values)
                logger.error(f"SNMP Error: {errorIndication}")
                raise Exception("Error querying SNMP data")
            elif errorStatus:
                if all_values:  # If we have any values, return them
                    return " | ".join(all_values)
                logger.error(f"Error Status: {errorStatus.prettyPrint()} at {errorIndex}")
                raise Exception("Error querying SNMP data")
            else:
                # Check if we've moved past our desired OID prefix
                if not varBinds or not str(varBinds[0][0]).startswith(oid[:-2]):
                    break
                    
                # Add the value to our results
                all_values.append(varBinds[0][1].prettyPrint())
                
                # Update OID for next query
                oid = str(varBinds[0][0])

        return " | ".join(all_values) if all_values else "No data"
                
    except Exception as e:
        logger.error(str(e))
        raise

# SNMP Printer State Mapping (hrPrinterStatus)
PRINTER_STATE_MAP = {
    "1": "Other",
    "2": "Unknown",
    "3": "Idle",
    "4": "Printing",
    "5": "Warming Up"
}

async def monitor_printer_status() -> None:
    """Monitor printer status via SNMP"""
    global printer_error, current_page_count,printer_ip,printer_state
    
    if not snmp_enabled:
        logger.info("SNMP monitoring disabled")
        return
    
    oid_data=printer_ref.child("oids").get()
    oids = {
        "status": oid_data.get("oid1",""),
        "pages_printed": oid_data.get("oid2",""),
        "toner_level": oid_data.get("oid3",""),
        "tray1": oid_data.get("oid4",""),
        "tray2": oid_data.get("oid5",""),
         "printer_state": oid_data.get("oid6",""),  # New OID for printer state (idle, printing, aborted)
    }
    
    error_count = 0
    status_flags = {
        "no_paper": False,
        "paper_jam": False,
        "no_toner": False,
        "connection_error": False,
        "cover": False,
    }
    
    status_flags_error_counter = {
        "no_paper": 0,
        "paper_jam": 0,
        "no_toner": 0,
        "connection_error": 0,
        "cover": 0,
    }
    snmpDispatcher = SnmpDispatcher()
    printer_state = None  # Variable to track the printer state (Idle, Printing, Aborted)
    
    while True:
        try:
            results = {}
            for name, oid in oids.items():
                results[name] = await query_printer_snmp(snmpDispatcher, oid, printer_ip)
                
            printer_error = False
            error_count = 0
            printer_ref.child("states").child("snmp").set(True)
            
            # Update printer status
            try:
                current_page_count = int(results['pages_printed'])
            except Exception as e:
                logger.error(f"Failed to update current page count: {e}--> {results['pages_printed']}")
            try:
                printer_state = results['printer_state']
            except Exception as e:
                logger.error(f"Failed to update printer state: {e}--> {results['printer_state']}")
            printer_ref.child("details").update({
                "pages_printed": results['pages_printed'],
                "tray_1": results['tray1'],
                "tray_2": results['tray2'],
                "toner_level": results['toner_level'],
                "printer_state": results['printer_state'],
            })
            
            # Check for errors
            status_message = results['status']
            
            if 'toner is out' in status_message.lower():
                printer_ref.child("details").update({
                        "status": "Inactive",
                        "status_message": "toner is out (waiting for user to refill)"
                    })
                status_flags["no_toner"] = True
                status_flags_error_counter["no_toner"] += 1
                if(status_flags_error_counter["no_toner"] > 300):
                    refund_all_print_jobs()
                    status_flags_error_counter["no_toner"] = 0                
                        
            if results['tray1'] == "0" and results['tray2'] == "0":
                printer_ref.child("details").update({
                    "status": "Inactive",
                    "status_message": "Printer is empty, please wait"
                })
                status_flags["no_paper"] = True
                status_flags_error_counter["no_paper"] += 1
                if(status_flags_error_counter["no_paper"] > 300):
                    refund_all_print_jobs()
                    status_flags_error_counter["no_paper"] = 0
                
            if "jam" in status_message.lower():
                printer_ref.child("details").update({
                    "status": "Inactive",
                    "status_message": "Paper jam (waiting for user to clear)"
                })
                status_flags["paper_jam"] = True
                status_flags_error_counter["paper_jam"] += 1
                if(status_flags_error_counter["paper_jam"] > 300):
                    refund_all_print_jobs()
                    status_flags_error_counter["paper_jam"] = 0            
            elif "empty" in status_message.lower() and "toner" in status_message.lower():
                refund_all_print_jobs()
                printer_ref.child("details").update({
                    "status": "Inactive",
                    "status_message": "Toner empty (10-100mins to refill)",
                    "error": "Toner empty"
                })
                status_flags["no_toner"] = True
            elif  'cover' in status_message.lower():
                printer_ref.child("details").update({
                    "status": "Inactive",
                    "status_message": "Printer cover is open (waiting for user to close)"
                })
                status_flags["cover"] = True
                status_flags_error_counter["cover"] += 1
                if(status_flags_error_counter["cover"] > 300):
                    refund_all_print_jobs()
                    status_flags_error_counter["cover"] = 0   
            else:
                printer_ref.child("details").child("error").set(status_message)

            # if "error" in status_message.lower():
            #     printer_ref.child("details").update({
            #         "status": "Inactive",
            #         "status_message": "Connection error (waiting for connection)"
            #     })
            #     status_flags["connection_error"] = True
            #     status_flags_error_counter["connection_error"] += 1
            #     if(status_flags_error_counter["connection_error"] > 300):
            #         refund_all_print_jobs()
            #         status_flags_error_counter["connection_error"] = 0        
            
            # Check for resolved errors
            if status_flags["no_paper"] and (results['tray1'] != "0" or results['tray2'] != "0"):
                printer_ref.child("details").update({
                    "status": "Active",
                    "status_message": "Printer is Active"
                })
                status_flags["no_paper"] = False
                status_flags_error_counter["no_paper"] = 0
                
            if status_flags["paper_jam"] and "paper jam" not in status_message.lower():
                printer_ref.child("details").update({
                    "status": "Active",
                    "status_message": "Printer is Active"
                })
                status_flags["paper_jam"] = False
                status_flags_error_counter["paper_jam"] = 0

            if status_flags["cover"] and "cover" not in status_message.lower():
                printer_ref.child("details").update({
                    "status": "Active",
                    "status_message": "Printer is Active"
                })
                status_flags["cover"] = False
                status_flags_error_counter["cover"] = 0
                
            if status_flags["no_toner"] and not ("empty" in status_message.lower() and "toner" in status_message.lower()):
                printer_ref.child("details").update({
                    "status": "Active",
                    "status_message": "Printer is Active"
                })
                status_flags["no_toner"] = False
                status_flags_error_counter["no_toner"] = 0
                     
            if status_flags["connection_error"]:
                printer_ref.child("details").update({
                    "status": "Active",
                    "status_message": "Printer is Active"
                })
                status_flags["connection_error"] = False
                status_flags_error_counter["connection_error"] = 0
            await asyncio.sleep(1)
            
        except Exception as e:
            error_count += 1
            if error_count > 3:
                printer_error = True
                error_count = 0
                printer_ref.child("states").child("snmp").set(False)
                
                try:
                    printer_ref.child("details").update({
                        "status": "Inactive",
                        "status_message": "Printer connection error"
                    })
                    status_flags["connection_error"] = True
                    # Try to reconnect
                    if not printer_dns_name:
                        printer_ip = printer_ref.child("details").child("ip").get()
                    else:
                        printer_ip = resolve_mdns_name(f"{printer_dns_name}.local")
                        
                except Exception as e:
                    logger.error(f"Failed to update printer status: {e}")
                    
            await asyncio.sleep(3)


def run_snmp_loop() -> None:
    """Run the SNMP monitoring loop"""
    asyncio.run(monitor_printer_status())


def process_print_job_with_snmp(user: str, filename: str) -> Tuple[bool, int]:
    """Process a single print job with SNMP monitoring"""
    file_ref = db.reference(f'users/{user}/printsdetails/{filename}')
    file_data = file_ref.get()
    
    if file_data["count"] == 0:
        file_ref.child("status").set("Done")
        file_ref.child("states").child("print").set(True)
        return True, 0
    
    try:
        # Get local file path
        file_ref.child("status").set("Downloading file...")
        file_ref.child("printprogress").set(0)
        local_file = download_print_file(file_data["link"], user, filename)
        file_ref.child("states").child("download").set(True)

        #logger.info("Cups Printing Progress")
        
        # Prepare print options
        options = {
            key: value.split(" ")[0] 
            for key, value in file_data["properties"].items()
        }
        options["copies"] = str(file_data["count"])
        
        # Submit print job with retries
        retry_count = 0
        print_job_id = None
        while retry_count < 5:
            retry_count += 1
            try:
                print_job_id = cups_connection.printFile(
                    printer_name.replace(" ", "_"),
                    os.path.abspath(local_file),
                    str(int(time.time())),
                    options
                )
                break
            except Exception as e:
                logger.error(f"Print job submission failed (attempt {retry_count}): {e}")
                if retry_count >= 5:
                    raise
                time.sleep(3)
        while 1:
            status, reasons = get_print_job_status(print_job_id)
            if status is None and reasons is None:
                return False, print_job_id
                
            if status == "Completed":
                logger.info(f"Print job completed: {print_job_id}")
                file_ref.child("states").child("print").set(True)
                return True, print_job_id
            elif status in ["Canceled", "Aborted", "Stopped"]:
                file_ref.child("status").set("Error at printer")
                file_ref.child("states").child("print").set(False)
                logger.error(f"Print job failed: {status} - {reasons}")
                handle_print_error(user, filename, f"Rejected by printer: {status} - {reasons}")
                return False, print_job_id

        file_ref.child("status").set("Printing...")
        return True, print_job_id
    
    except Exception as e:
        logger.error(f"Print job failed: {e}")
        file_ref.child("status").set("Printing error")
        file_ref.child("states").child("print").set(False)
        raise PrintJobError("Print job processing failed")


# def process_print_job_with_snmp(user: str, filename: str) -> Tuple[bool, int]:
#     global pagecount_before
#     """Process a single print job with SNMP monitoring"""
#     file_ref = db.reference(f'users/{user}/printsdetails/{filename}')
#     file_data = file_ref.get()
    
#     if file_data["count"] == 0:
#         file_ref.child("status").set("Done")
#         file_ref.child("states").child("print").set(True)
#         return True, 0
    
#     try:
#         # Download file
#         file_ref.child("status").set("Downloading file...")
#         file_ref.child("printprogress").set(0)
#         local_file = download_print_file(file_data["link"], user, filename)
#         file_ref.child("states").child("download").set(True)

#         #logger.info("Cups Printing Progress")
        
#         # Prepare print options
#         options = {
#             key: value.split(" ")[0] 
#             for key, value in file_data["properties"].items()
#         }
#         options["copies"] = str(file_data["count"])
        
#         #  # --- Wait for printer to become idle using global printer_state ---
#         waited = 0
#         max_wait = 300
#         interval = 2

#         # Check printer state directly (3 = Idle, 4 = Printing)
#         if str(printer_state) != "3":
#             file_ref.child("status").set("Waiting for printer to become idle...")
#             while waited < max_wait:
#                 if str(printer_state) == "3":
#                     break
#                 time.sleep(interval)
#                 waited += interval
#             if waited >= max_wait:
#                 file_ref.child("status").set("Printer busy or unavailable")
#                 file_ref.child("states").child("print").set(False)
#                 logger.error("Printer did not become idle in time.")
#                 return False, None

#         # # 1. Capture page count before the user's job starts
#         pagecount_before = current_page_count
        
#         # # Submit print job with retries
#         retry_count = 0
#         print_job_id = None
#         while retry_count < 5:
#             retry_count += 1
#             try:
#                 print_job_id = cups_connection.printFile(
#                     printer_name.replace(" ", "_"),
#                     os.path.abspath(local_file),
#                     str(int(time.time())),
#                     options
#                 )
#                 break
#             except Exception as e:
#                 logger.error(f"Print job submission failed (attempt {retry_count}): {e}")
#                 if retry_count >= 5:
#                     raise
#                 time.sleep(3)
        
#         while 1:
#             status, reasons = get_print_job_status(print_job_id)
#             if status is None and reasons is None:
#                 return False, print_job_id
                
#             if status == "Completed":
#                 logger.info(f"Print job completed: {print_job_id}")
#                 file_ref.child("states").child("print").set(True)
#                 return True, print_job_id
#             elif status in ["Canceled", "Aborted", "Stopped"]:
#                 file_ref.child("status").set("Error at printer")
#                 file_ref.child("states").child("print").set(False)
#                 logger.error(f"Print job failed: {status} - {reasons}")
#                 handle_print_error(user, filename, f"Rejected by printer: {status} - {reasons}")
#                 return False, print_job_id

#         file_ref.child("status").set("Printing...")
#         return True, print_job_id

#     except Exception as e:
#         logger.error(f"Print job failed: {e}")
#         file_ref.child("status").set("Printing error")
#         file_ref.child("states").child("print").set(False)
#         raise PrintJobError("Print job processing failed")
def cancel_all_print_jobs(error: str = "Printing error") -> None:
    """Cancel all pending print jobs (without refunds)"""
    try:
        ref = db.reference(f"Printers/{config['printer_id']}/printstodo")
        jobs = ref.get()
        
        if not jobs:
            return
            
        for job_id, job_data in jobs.items():
            user = job_data["user"]
            files = job_data["files"].split(",")
            printing = job_data.get("done_printing", 0)
            for file in files[printing:]:
                handle_print_error(user, file, error)
                
        ref.delete()
    except Exception as e:
        logger.error(f"Failed to cancel all jobs: {e}")
        ref.delete()

def process_print_job_without_snmp(user: str, filename: str) -> Tuple[bool, int]:
    """Process a single print job without SNMP monitoring"""
    file_ref = db.reference(f'users/{user}/printsdetails/{filename}')
    file_data = file_ref.get()
    
    if file_data["count"] == 0:
        file_ref.child("status").set("Done")
        file_ref.child("states").child("print").set(True)
        return True, 0
    
    try:
        # Download file
        file_ref.child("status").set("Downloading file...")
        file_ref.child("printprogress").set(0)
        local_file = download_print_file(file_data["link"], user, filename)
        file_ref.child("states").child("download").set(True)
        logger.info("File downloaded successfully")
        
        # Prepare print options
        options = {
            key: value.split(" ")[0] 
            for key, value in file_data["properties"].items()
        }
        options["copies"] = str(file_data["count"])
        
        # Submit print job
        print_job_id = cups_connection.printFile(
            printer_name,
            os.path.abspath(local_file),
            str(int(time.time())),
            options
        )
        
        file_ref.child("status").set("Printing...")
        
        # Monitor job status directly
        start_time = time.time()
        while time.time() - start_time < MAX_PRINT_JOB_WAIT_TIME:
            status, reasons = get_print_job_status(print_job_id)
            
            if status is None and reasons is None:
                return False, print_job_id
                
            if status == "Completed":
                logger.info(f"Print job completed: {print_job_id}")
                file_ref.child("states").child("print").set(True)
                return True, print_job_id
            elif status in ["Canceled", "Aborted", "Stopped"]:
                file_ref.child("status").set("Error at printer")
                file_ref.child("states").child("print").set(False)
                logger.error(f"Print job failed: {status} - {reasons}")
                return False, print_job_id
                
            time.sleep(0.5)
        
        # Timeout reached
        file_ref.child("status").set("Printing timeout")
        file_ref.child("states").child("print").set(False)
        return False, print_job_id
        
    except Exception as e:
        logger.error(f"Print job failed: {e}")
        file_ref.child("status").set("Printing error")
        file_ref.child("states").child("print").set(False)
        raise PrintJobError("Print job processing failed")

def process_print_queue_for_snmp(event_key: str, job_data: Dict) -> None:
    """Process a print queue job with status tracking using threading"""
    logger.info("got data")
    global printer_error, internet_error
    user = ""
    try:
        if event_key:
            files = job_data["files"].split(",")
            logger.info(files)
            user = job_data["user"]
            user_ref = db.reference(f'users/{user}/details')
            init_page_count = current_page_count
            printing_pages = []
            job_ids = []
            total_cost = 0
            total_pc=0
            printed_sum = 0
            i = 0
            
            # Define thread function for processing print jobs
            def print_processing_thread():
                nonlocal total_cost, printing_pages, job_ids,total_pc
                try:
                    for count, filename in enumerate(files, 1):
                        logger.info(filename)
                        try:
                            # Update job status
                            db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').update({
                                "printing": count,
                                "done_printing": i,
                                "user": user,
                                "files": job_data["files"]
                            })
                            logger.info(f"Printing: {filename}")
                            
                            # Calculate cost (for tracking only, no refunds)
                            file_cost = db.reference(f'users/{user}/printsdetails/{filename}').child('cost').get()
                            total_cost += file_cost
                            
                            # Process the print job
                            success, job_id = process_print_job_with_snmp(user, filename)
                            
                            if success:
                                # Calculate pages based on original code's logic
                                up_c = 1  # int(db.reference(f'users/{user}/printsdetails/{filename}/properties').child('count_per_page').get().split(" ")[0])
                                total_pc += math.ceil(db.reference(f'users/{user}/printsdetails/{filename}').child('pagecount').get() / up_c) * db.reference(f'users/{user}/printsdetails/{filename}').child('count').get()
                                printing_pages.append(total_pc)
                                job_ids.append(job_id)
                                logger.info("Sent to printer")
                            else:
                                printing_pages.append(0)
                                job_ids.append(job_id)
                                handle_print_error(user, filename, "Printing error")
                        except Exception as e:
                            printing_pages.append(0)
                            job_ids.append(0)
                            logger.error(f"Error at printing {filename}: {e}")
                            handle_print_error(user, filename)
                except Exception as e:
                    logger.error(f"Error in print thread: {e}")
            
            # Start the thread for print processing
            print_thread = threading.Thread(target=print_processing_thread)
            print_thread.daemon = True
            print_thread.start()
            
            # Monitor printing progress in the main thread
            while True:
                pages_printed = int(current_page_count) - int(init_page_count)
                
                # Make sure we have data for the current index
                if i < len(files) and len(printing_pages) > i:
                    # Update progress in the database
                    db.reference(f'users/{user}/printsdetails/{files[i]}').child("printed").set(
                        f"{pages_printed-printed_sum}/{printing_pages[i]-printed_sum}"
                    )
                    
                    # Check if current file is done printing
                    if pages_printed >= printing_pages[i]:
                        printed_sum = printing_pages[i]
                        db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("Done printing")
                        db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').child("done_printing").set(i+1)
                        i += 1
                        
                        # All files are done
                        if i == len(files):
                            db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').delete()
                            db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
                                datetime.datetime.now().strftime("%d-%m-%y")
                            ).push().set({
                                "user": job_data["user"],
                                "user_id": user_ref.child("atomte_id").get(),
                                "files": job_data["files"],
                                "status": "Success",
                                "time": datetime.datetime.now().isoformat(),
                                "name": user_ref.child("name").get(),
                                "totalcost": total_cost
                            })
                            break
                
                # Check for errors
                if printer_error or internet_error:
                    cancel_all_print_jobs(error="Error at printer taking too long try again")
                    db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
                        datetime.datetime.now().strftime("%d-%m-%y")
                    ).push().set({
                        "user": job_data["user"],
                        "user_id": user_ref.child("atomte_id").get(),
                        "files": job_data["files"],
                        "status": "Error",
                        "time": datetime.datetime.now().isoformat(),
                        "name": user_ref.child("name").get(),
                        "totalcost": total_cost
                    })
                    logger.error('Error at page count diff printer_error')
                    break
                
                # Check if print thread is still alive
                if not print_thread.is_alive() and i >= len(printing_pages):
                    # Thread is done and all files processed
                    break
                    
                time.sleep(1)
                
    except Exception as e:
        logger.error(f'Error in print queue processing: {str(e)}')
        try:
            db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').delete()
            db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
                datetime.datetime.now().strftime("%d-%m-%y")
            ).push().set({
                "user": job_data["user"],
                "user_id": user_ref.child("atomte_id").get() if user_ref else "unknown",
                "files": job_data["files"],
                "status": "Error",
                "time": datetime.datetime.now().isoformat(),
                "name": user_ref.child("name").get() if user_ref else "unknown",
                "totalcost": total_cost
            })
        except Exception as nested_e:
            logger.error(f"Failed to clean up failed job: {nested_e}")



# def process_print_queue_for_snmp(event_key: str, job_data: Dict) -> None:
#     """Process a print queue job with status tracking using threading"""
#     global printer_error, internet_error, conn,printer,pagecount_before
#     user = ""
#     try:
#         if event_key:
#             files = job_data["files"].split(",")
#             user = job_data["user"]
#             user_ref = db.reference(f'users/{user}/details')
#             init_page_count = current_page_count
#             printing_pages = [] #tracking pages for each file
#             job_ids = []
#             total_cost = 0
#             printed_sum = 0
#             total_pc=0
#             i = 0 # Index for the current file being processed
            
#             # Define thread function for processing print jobs
#             def print_processing_thread():
#                 nonlocal total_cost, printing_pages, job_ids, total_pc
#                 global pagecount_before
#                 try:
#                     for count, filename in enumerate(files, 1):
#                         try:
#                             # Wait for printer to become idle before starting this file
#                             # waited = 0
#                             # max_wait = 300
#                             # interval = 2
#                             # while str(printer_state) != "3" and waited < max_wait:
#                             #     if waited == 0:
#                             #         db.reference(f'users/{user}/printsdetails/{filename}').child("status").set("Waiting for printer to become idle...")
#                             #     time.sleep(interval)
#                             #     waited += interval
#                             # if waited >= max_wait:
#                             #     db.reference(f'users/{user}/printsdetails/{filename}').child("status").set("Printer busy or unavailable")
#                             #     handle_print_error(user, filename, "Printer did not become idle in time.")
#                             #     printing_pages.append(total_pc)
#                             #     job_ids.append(0)
#                             #     continue
#                             # Update job status
#                             db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').update({
#                                 "printing": count,
#                                 "done_printing": i,
#                                 "user": user,
#                                 "files": job_data["files"]
#                             })
#                             logger.info(f"Printing: {filename}")

#                             # Calculate cost
#                             file_cost = db.reference(f'users/{user}/printsdetails/{filename}').child('cost').get()
#                             total_cost += file_cost

#                             # Process the print job
#                             success, job_id = process_print_job_with_snmp(user, filename)
#                             if  success and job_id:
                                
#                                 up_c = 1  # int(db.reference(f'users/{user}/printsdetails/{filename}/properties').child('count_per_page').get().split(" ")[0])
#                                 total_pc += math.ceil(db.reference(f'users/{user}/printsdetails/{filename}').child('pagecount').get() / up_c) * db.reference(f'users/{user}/printsdetails/{filename}').child('count').get()
#                                 printing_pages.append(total_pc)
#                                 job_ids.append(job_id)
#                                 logger.info("Sent to printer")
#                                 # if int(init_page_count) != int(current_page_count):
#                                 #     logger.warning(f"Printer used externally: init={init_page_count}, current={current_page_count}")
#                                 #     pagecount_before = int(current_page_count)
#                                 # else:
#                                 #     pagecount_before = int(init_page_count)
                            
#                             else:
#                                 printing_pages.append(total_pc)
#                                 job_ids.append(job_id)
#                                 handle_print_error(user, filename, "printing error")

#                         except Exception as e:
#                             printing_pages.append(total_pc)
#                             job_ids.append(0)
#                             logger.error(f"Error at printing {filename}: {e}")
#                             handle_print_error(user, filename, f"{type(e).__name__}: {e}")
#                 except Exception as e:
#                     logger.error(f"Error in print thread: {e}")

            
#             # Start the thread for print processing
#             print_thread = threading.Thread(target=print_processing_thread)
#             print_thread.daemon = True
#             print_thread.start()
     
#             # Monitor printing progress in the main thread
#             while True:
            
#                 try:
#                     pages_printed = int(current_page_count) - int(pagecount_before) 
#                 except Exception as e:
#                     logger.error(f"Error getting current page count: {e}---{current_page_count}---{init_page_count}")
#                     logger.error(f"Error getting page count: {e}")
        
#                 # Make sure we have data for the current index
#                 if i < len(files) and len(printing_pages) > i:
#                     # Update progress in the database
#                     db.reference(f'users/{user}/printsdetails/{files[i]}').child("printed").set(
#                         f"{pages_printed-printed_sum}/{printing_pages[i]-printed_sum}"
#                     )
                    
#                     # Check if current file is done printing
#                     if pages_printed >= printing_pages[i]:
#                         printed_sum = printing_pages[i]
#                         db.reference(f'users/{user}/printsdetails/{files[i]}').child("status").set("Done printing")
#                         db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').child("done_printing").set(i+1)
#                         i += 1
                        
#                         # All files are done
#                         if i == len(files):
#                             db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').delete()
#                             db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
#                                 datetime.datetime.now().strftime("%d-%m-%y")
#                             ).push().set({
#                                 "user": job_data["user"],
#                                 "user_id": user_ref.child("atomte_id").get(),
#                                 "files": job_data["files"],
#                                 "status": "Success",
#                                 "time": datetime.datetime.now().isoformat(),
#                                 "name": user_ref.child("name").get(),
#                                 "totalcost": total_cost
#                             })
#                             break
                   
#                 # Check for errors
#                 if printer_error or internet_error:
                
#                     refund_all_print_jobs(error="Error at printer taking too long try again")
#                     db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
#                         datetime.datetime.now().strftime("%d-%m-%y")
#                     ).push().set({
#                         "user": job_data["user"],
#                         "user_id": user_ref.child("atomte_id").get(),
#                         "files": job_data["files"],
#                         "status": "Error",
#                         "time": datetime.datetime.now().isoformat(),
#                         "name": user_ref.child("name").get(),
#                         "totalcost": total_cost
#                     })
#                     logger.error('Error at page count diff printer_error')
#                     break
                
#                 # Check if print thread is still alive
#                 if not print_thread.is_alive() and i >= len(printing_pages):
#                     # Thread is done and all files processed
#                     break
                    
#                 time.sleep(1)
                
#     except Exception as e:
#         logger.error(f'Error in print queue processing: {str(e)}')
#         try:
#             db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').delete()
#             db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
#                 datetime.datetime.now().strftime("%d-%m-%y")
#             ).push().set({
#                 "user": job_data["user"],
#                 "user_id": user_ref.child("atomte_id").get() if user_ref else "unknown",
#                 "files": job_data["files"],
#                 "status": "Error",
#                 "time": datetime.datetime.now().isoformat(),
#                 "name": user_ref.child("name").get() if user_ref else "unknown",
#                 "totalcost": total_cost
#             })
#         except Exception as nested_e:
#             logger.error(f"Failed to clean up failed job: {nested_e}")

def process_print_queue_non_snmp(event_key: str, job_data: Dict) -> None:
    """Process a print queue job"""
    global printer_error, internet_error
    
    try:
        files = job_data["files"].split(",")
        user = job_data["user"]
        user_ref = db.reference(f'users/{user}/details')
        total_cost = 0
        
        # Process each file in the job
        for i, filename in enumerate(files):
            try:
                # Update job status
                db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').update({
                    "printing": i + 1,
                    "done_printing": i,
                    "user": user,
                    "files": ",".join(files)
                })
                
                logger.info(f"Processing file: {filename}")
                
                # Calculate cost
                file_cost = db.reference(f'users/{user}/printsdetails/{filename}').child('cost').get()
                total_cost += file_cost
                
                # Print file based on SNMP availability
                if snmp_enabled:
                    success, job_id = process_print_job_with_snmp(user, filename)
                else:
                    success, job_id = process_print_job_without_snmp(user, filename)
                
                if not success:
                    handle_print_error(user, filename, "Printing error")
                
            except Exception as e:
                logger.error(f"Failed to process file {filename}: {e}")
                handle_print_error(user, filename, f"{type(e).__name__}: {e}")
        
        # Job completed successfully
        db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').delete()
        db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
            datetime.datetime.now().strftime("%d-%m-%y")
        ).push().set({
            "user": job_data["user"],
            "user_id": user_ref.child("atomte_id").get(),
            "files": job_data["files"],
            "status": "Success",
            "time": datetime.datetime.now().isoformat(),
            "name": user_ref.child("name").get(),
            "totalcost": total_cost
        })
        
    except Exception as e:
        logger.error(f"Print queue processing failed: {e}")
        try:
            db.reference(f'Printers/{config["printer_id"]}/printeddetails').child(
                datetime.datetime.now().strftime("%d-%m-%y")
            ).push().set({
                "user": job_data["user"],
                "user_id": user_ref.child("atomte_id").get(),
                "files": job_data["files"],
                "status": "Error",
                "time": datetime.datetime.now().isoformat(),
                "name": user_ref.child("name").get(),
                "totalcost": total_cost
            })
            db.reference(f'Printers/{config["printer_id"]}/printstodo/{event_key}').delete()
        except Exception as e:
            logger.error(f"Failed to clean up failed job: {e}")


def on_print_job_added(event) -> None:
    """Handle new print jobs added to the queue"""
    global active_listeners
    
    jobs = db.reference(f'Printers/{config["printer_id"]}/printstodo').get()
    if jobs:
        first_job = next(iter(jobs.items()), None)
        if first_job:
            job_id, job_data = first_job
            logger.info(f"New print job: {job_id}")
            if snmp_enabled:
                process_print_queue_for_snmp(job_id, job_data)
            else:
                process_print_queue_non_snmp(job_id, job_data)


def main() -> None:
    """Main application loop"""
    global printer_ip, active_listeners
    
    try:
        initialize_system()
        
        while True:
            try:
                if not ping_printer(printer_ip):
                    raise PrinterConnectionError("Printer is not connected - Ping failed")
                
                # Update printer status
                printer_ref.child("states").child("printer_connection").set(True)
                printer_ref.child("details").update({
                    "status": "Active",
                    "status_message": "Printer is now Active"
                })
                
                # Set up print job listener
                ref = db.reference(f'Printers/{config["printer_id"]}/printstodo')
                listener = ref.listen(on_print_job_added)
                active_listeners.append(listener)
                
                # Monitor listener and connection status
                while True:
                    if internet_error or printer_error:
                        logger.error(f"Connection issues detected - Internet: {internet_error}, Printer: {printer_error}")
                        for lst in active_listeners:
                            lst.close()
                        active_listeners = []
                        raise NetworkError("Connection error")
                    
                    if not all(lst._thread.is_alive() for lst in active_listeners):
                        raise PrinterConnectionError("Listener thread died")
                    
                    time.sleep(PRINTER_CHECK_INTERVAL)
                    
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                try:
                    refund_all_print_jobs("System error")
                except Exception as refund_error:
                    logger.error(f"Failed to refund all jobs: {refund_error}")
                
                # Clean up listeners
                for lst in active_listeners:
                    lst.close()
                active_listeners = []
                
                # Update status
                try:
                    printer_ref.child("states").child("printer_connection").set(False)
                    printer_ref.child("details").update({
                        "status": "Inactive",
                        "status_message": "Something went wrong"
                    })
                except Exception as e:
                    logger.error(f"Failed to update status: {e}")
                
                time.sleep(PRINTER_CHECK_INTERVAL)
                
    except Exception as e:
        logger.error(f"Fatal initialization error: {e}")
        raise


if __name__ == "__main__":
    main()