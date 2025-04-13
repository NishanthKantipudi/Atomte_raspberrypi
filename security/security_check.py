import os
import subprocess
import shutil
import logging

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AtomteSecurity")

SERIAL_FILE = "security/cpu_serial.txt"
SECURE_DIRECTORY = "../../Atomte"

def get_cpu_serial():
    try:
        result = subprocess.run(
            ["cat", "/proc/cpuinfo"], capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Serial"):
                return line.split(":")[1].strip()
    except Exception as e:
        logger.error(f"Error fetching CPU serial: {e}")
    return None

def clear_crontab():
    try:
        subprocess.run(["crontab", "-r"], check=True)
        logger.info("Crontab cleared successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error clearing crontab: {e}")

def secure_system():
    current_serial = get_cpu_serial()
    if not current_serial:
        logger.error("Unable to fetch CPU serial number. Aborting security check.")
        return

    if os.path.exists(SERIAL_FILE):
        try:
            with open(SERIAL_FILE, "r") as f:
                stored_serial = f.read().strip()
        except Exception as e:
            logger.error(f"Error reading stored CPU serial: {e}")
            return

        if current_serial != stored_serial:
            logger.warning("CPU serial mismatch detected. Securing the system...")
            try:
                if os.path.exists(SECURE_DIRECTORY):
                    shutil.rmtree(SECURE_DIRECTORY)
                    logger.info(f"Directory '{SECURE_DIRECTORY}' has been deleted.")
                else:
                    logger.info(f"Directory '{SECURE_DIRECTORY}' does not exist.")
            except Exception as e:
                logger.error(f"Error deleting directory '{SECURE_DIRECTORY}': {e}")
            clear_crontab()
        else:
            logger.info("CPU serial matches. Security check passed.")
    else:
        logger.info("No stored CPU serial found. Storing the current serial.")
        try:
            with open(SERIAL_FILE, "w") as f:
                f.write(current_serial)
            logger.info("CPU serial stored successfully.")
        except Exception as e:
            logger.error(f"Error storing CPU serial: {e}")

if __name__ == "__main__":
    secure_system()
#6e6ab026f81de610