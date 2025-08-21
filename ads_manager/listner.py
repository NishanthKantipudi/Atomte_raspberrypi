import firebase_admin
from firebase_admin import credentials, db
import requests,shutil
import os
import json
import time
from urllib.parse import urlparse
import logging
import threading

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== SETUP ==========
cwd = os.getcwd()
CONFIG_PATH = os.path.join(cwd, "../secrets/details.json")

def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Failed to read config file {file_path}: {e}")
        return None

data = read_json_file(CONFIG_PATH)
if not data:
    logger.error("Failed to load configuration. Exiting.")
    exit(1)

# ========== CONFIG ==========
PRINTER_ID = data["code"]  # <-- Replace this with actual printer_id
VIDEO_FOLDER = cwd + '/ads_manager/videos'
JSON_STATE_FILE = cwd+'/ads_manager/video_state.json'
MAX_RETRY_COUNT = 5
RETRY_DELAY = 10  # seconds

# ========== INIT FIREBASE ==========
def initialize_firebase():
    try:
        cred_path = cwd + "/secrets/key.json"
        KEY_PATH = "/dev/shm/atomte_secrets.json"
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
            'httpTimeout': 10
        })
        logger.info("Firebase initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False

# ========== HELPER FUNCTIONS ==========
def load_stored_links():
    try:
        if os.path.exists(JSON_STATE_FILE):
            with open(JSON_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load stored links: {e}")
    return {}

def save_links(data):
    try:
        with open(JSON_STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save links: {e}")

def download_video(url, filename):
    try:
        filepath = os.path.join(VIDEO_FOLDER, filename)
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                shutil.copyfileobj(r.raw, f)  # faster streaming
        logger.info(f"Downloaded: {filename}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def get_filename_from_url(url):
    try:
        parsed = urlparse(url)
        return os.path.basename(parsed.path)
    except Exception:
        # Fallback to a timestamp if URL parsing fails
        return f"video_{int(time.time())}.mp4"

# ========== MAIN LOGIC ==========
def process_videos():
    try:
        ref = db.reference(f'Printers/{PRINTER_ID}/videos')
        videos = ref.get()
        if not videos:
            logger.info("No videos found.")
            return True

        os.makedirs(VIDEO_FOLDER, exist_ok=True)
        old_links = load_stored_links()
        new_links = {}

        for key, url in videos.items():
            new_links[key] = url
            old_url = old_links.get(key)
            if old_url != url:
                logger.info(f"📥 Change detected or new video: {key}")
                filename = get_filename_from_url(url)
                download_video(url, key + ".mp4")

        save_links(new_links)
        return True
    except Exception as e:
        logger.error(f"Error processing videos: {e}")
        return False

# ========== LISTENER MANAGEMENT ==========
listeners = []

def check_listener_health():
    for listener in listeners:
        if hasattr(listener, '_thread') and not listener._thread.is_alive():
            return False
    return True

def close_all_listeners():
    global listeners
    for listener in listeners:
        try:
            listener.close()
        except Exception as e:
            logger.error(f"Error closing listener: {e}")
    listeners = []

# ========== LISTENERS ==========
def data_load_listener(event):
    try:
        value = event.data
        if value is True:
            logger.info(f"🟢 data_load triggered for printer: {PRINTER_ID}")
            process_videos()
            # Reset the flag
            try:
                db.reference(f'Printers/{PRINTER_ID}/load_data').set(False)
            except Exception as e:
                logger.error(f"Failed to reset load_data flag: {e}")
    except Exception as e:
        logger.error(f"Error in data_load_listener: {e}")

def setup_listeners():
    global listeners
    close_all_listeners()
    
    try:
        # Setup video load_data listener
        load_data_ref = db.reference(f'Printers/{PRINTER_ID}/load_data')
        listener = load_data_ref.listen(data_load_listener)
        listeners.append(listener)
        logger.info("Set up load_data listener")
        
        # Setup additional listeners as needed
        # Example from your code:
        printer_ref = db.reference(f'Printers/{PRINTER_ID}')
        
        # Uncomment and implement these as needed:
        # audio_listener = printer_ref.child("audio").listen(audio_handler)
        # listeners.append(audio_listener)
        # mic_listener = printer_ref.child("mic").listen(mic_handler)
        # listeners.append(mic_listener)
        
        return True
    except Exception as e:
        logger.error(f"Failed to setup listeners: {e}")
        return False

# ========== MAIN EXECUTION ==========
def main():
    retry_count = 0
    
    while True:
        try:
            # Initialize Firebase if not already initialized
            if not firebase_admin._apps:
                if not initialize_firebase():
                    logger.error("Firebase initialization failed, retrying...")
                    time.sleep(RETRY_DELAY)
                    continue
            
            # Setup listeners
            if not setup_listeners():
                raise Exception("Failed to set up listeners")
            
            logger.info("All listeners set up successfully. Monitoring...")
            retry_count = 0  # Reset retry count on successful setup
            
            # Monitor listener health
            while True:
                time.sleep(10)
                
                # Check network connectivity
                try:
                    requests.get("https://skilldevelopmentapp-default-rtdb.firebaseio.com/", timeout=5)
                except requests.exceptions.RequestException:
                    logger.warning("Network connectivity issue detected")
                    time.sleep(RETRY_DELAY)
                    raise Exception("Network error")
                
                # Check if all listeners are alive
                if not check_listener_health():
                    raise Exception("Listener thread died")
                
                # Process videos periodically if needed
                # process_videos()
                
        except Exception as e:
            retry_count += 1
            logger.error(f"Error in main loop (attempt {retry_count}/{MAX_RETRY_COUNT}): {str(e)}")
            
            # Close any existing listeners
            close_all_listeners()
            
            # If we've exceeded max retries, add a longer delay
            if retry_count >= MAX_RETRY_COUNT:
                logger.error(f"Maximum retry count ({MAX_RETRY_COUNT}) reached. Taking a longer break.")
                time.sleep(RETRY_DELAY * 3)
                retry_count = 0
            else:
                time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()
