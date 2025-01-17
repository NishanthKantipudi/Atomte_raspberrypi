import os
import requests
import time
from datetime import datetime, timedelta
import threading
import firebase_admin
from firebase_admin import credentials, db
import json

cwd = os.getcwd()
cred = credentials.Certificate(cwd+"/../secrets/key.json")
firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://skilldevelopmentapp-default-rtdb.firebaseio.com/',
        'httpTimeout':10
})

SAVE_DIRECTORY = os.path.join(os.getcwd()+"/../atomte/src/MainScreen", "ads")
os.makedirs(SAVE_DIRECTORY, exist_ok=True)

def download_video(url, filename):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        file_path = os.path.join(SAVE_DIRECTORY, filename)
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"Downloaded: {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {filename}: {e}")



def delete_video(filename):
    file_path = os.path.join(SAVE_DIRECTORY, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted: {filename}")
    else:
        print(f"File not found for deletion: {filename}")

def process_ads(ads_data):
    now = datetime.now()
    for ad in ads_data:
        date = ad.get("date")
        time_slots = ad.get("time_slots", [])
        for time_slot in time_slots:
            start_time_str, end_time_str = time_slot["slot"].split(" to ")
            url = time_slot["url"]
            start_time = datetime.strptime(f"{date} {start_time_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{date} {end_time_str}", "%Y-%m-%d %H:%M")
            filename = f"ad{time_slot['place'].replace('place', '')}.mp4"
            # Download immediately if within the time slot
            if start_time <= now < end_time:
                print(f"Downloading {filename} immediately.")
                threading.Thread(target=download_video, args=(url, filename)).start()

            # Schedule deletion after the time slot
            

# Function to fetch ads data from Firebase
def fetch_ads_data():
    def read_json_file(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    main_data = read_json_file(cwd+"/../secrets/details.json")
    main_data["printer_id"] = main_data["code"]
    ref = db.reference("Printers/"+str(main_data["printer_id"])+"/ads")  # Replace 'ads' with your Firebase node name
    ads_data = ref.get()
    if ads_data:
        structured_data = []
        for date, entries in ads_data.items():
            time_slots = []
            for time_slot, info in entries.items():
                for placename, url in info.items():
                    time_slots.append({"slot": time_slot, "place": placename, "url": url["url"]})
            structured_data.append({"printer_id": main_data["printer_id"], "date": date, "time_slots": time_slots})
        return structured_data
    return []



def run_scheduler():
    while True:
        # Get the current time
        now = datetime.now()
        
        # Calculate the next hour
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        
        # Calculate the delay until the next hour
        delay = (next_hour - now).total_seconds()
        
        print(f"Fetching data from Firebase at {now.strftime('%Y-%m-%d %H:%M:%S')}...")
        ads_data = fetch_ads_data()
        print(ads_data)
        if ads_data:
            process_ads(ads_data)
        else:
            print("No ads data found.")
        
        print(f"Next fetch scheduled at {next_hour.strftime('%Y-%m-%d %H:%M:%S')}. Waiting for {int(delay)} seconds...")
        time.sleep(delay)


if __name__ == "__main__":
    print("Starting the ad scheduling service...")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Keep the script running
    while True:
        time.sleep(1)
