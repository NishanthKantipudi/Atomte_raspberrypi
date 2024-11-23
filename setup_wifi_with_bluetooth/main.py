import logging

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()

import asyncio
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "0000180A-0000-1000-8000-00805F9B34FB"  # Replace with Android service UUID
CHARACTERISTIC_UUID = "00002a29-0000-1000-8000-00805f9b34fb"  # Replace with Android characteristic UUID

async def connect_and_read_data():
    logger.info("Scanning for devices...")
    devices = await BleakScanner.discover()
    for device in devices:

        logger.info(f"{str(device)}Found device: {device.name} ({device.address})")
        if "POCO F5" in device.name:  # Replace with your Android device name
            async with BleakClient(device.address) as client:
                logger.info(f"Connected to {device.name}")
                data = await client.read_gatt_char(CHARACTERISTIC_UUID)
                logger.info(f"Received data: {data.decode()}")  # Assuming data is text

# Run the script
asyncio.run(connect_and_read_data())


