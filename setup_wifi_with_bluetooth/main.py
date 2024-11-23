import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.scanner import AdvertisementData
from bleak.backends.device import BLEDevice
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define UUIDs - make sure these match your Android app
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"

async def handle_data(sender: int, data: bytearray):
    """Handle incoming data from connected device"""
    try:
        decoded_data = data.decode()
        logger.info(f"Received data: {decoded_data}")
        # Process your data here
        return decoded_data
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return None

async def scan_and_connect():
    """Scan for and connect to the first found device"""
    logger.info("Starting BLE scan...")
    
    devices = await BleakScanner.discover()
    for device in devices:
        logger.info(f"Found device: {device.name} ({device.address})")
        
        try:
            async with BleakClient(device.address) as client:
                logger.info(f"Connected to {device.address}")
                
                # Discover services
                services = await client.get_services()
                for service in services:
                    logger.info(f"Service: {service.uuid}")
                    for char in service.characteristics:
                        logger.info(f"  Characteristic: {char.uuid}")
                        
                # Subscribe to notifications if the characteristic supports it
                for service in services:
                    for char in service.characteristics:
                        if "notify" in char.properties:
                            logger.info(f"Subscribing to notifications for {char.uuid}")
                            await client.start_notify(char.uuid, handle_data)
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error connecting to device: {e}")

async def main():
    """Main function to run the BLE client"""
    try:
        await scan_and_connect()
    except Exception as e:
        logger.error(f"Main loop error: {e}")
    finally:
        logger.info("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())