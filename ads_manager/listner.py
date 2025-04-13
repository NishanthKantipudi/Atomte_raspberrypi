import firebase_admin
from firebase_admin import credentials, db
import requests
import os
import json
from urllib.parse import urlparse
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== SETUP ==========
cwd = os.getcwd()
CONFIG_PATH = os.path.join(cwd, "../secrets/details.json")
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

data = read_json_file(CONFIG_PATH)

# ========== CONFIG ==========
PRINTER_ID = data["code"]  # <-- Replace this with actual printer_id
VIDEO_FOLDER = 'videos'
JSON_STATE_FILE = 'video_state.json'

# ========== INIT FIREBASE ==========

cred = credentials.Certificate(cwd+"/secrets/key.json")
firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout':10
})

# ========== HELPER FUNCTIONS ==========
def load_stored_links():
    if os.path.exists(JSON_STATE_FILE):
        with open(JSON_STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_links(data):
    with open(JSON_STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def download_video(url, filename):
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        filepath = os.path.join(VIDEO_FOLDER, filename)
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"✅ Downloaded: {filename}")
    except Exception as e:
        logger.info(f"❌ Failed to download {url}: {e}")

def get_filename_from_url(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)

# ========== MAIN LOGIC ==========
def process_videos():
    ref = db.reference(f'Printers/{PRINTER_ID}/videos')
    videos = ref.get()

    if not videos:
        logger.info("No videos found.")
        return

    os.makedirs(VIDEO_FOLDER, exist_ok=True)

    old_links = load_stored_links()
    new_links = {}

    for key, url in videos.items():
        new_links[key] = url
        old_url = old_links.get(key)

        if old_url != url:
            logger.info(f"📥 Change detected or new video: {key}")
            filename = get_filename_from_url(url)
            download_video(url, key+".mp4")

    save_links(new_links)

# ========== LISTENER ==========
def listener(event):
    value = event.data
    if value is True:
        logger.info(f"🟢 data_load triggered for printer: {PRINTER_ID}")
        process_videos()
        # Optional: reset the flag
        db.reference(f'Printers/{PRINTER_ID}/load_data').set(False)

# ========== ATTACH LISTENER ==========
def main():
    ref = db.reference(f'Printers/{PRINTER_ID}/load_data')
    ref.listen(listener)

if __name__ == "__main__":
    main()
