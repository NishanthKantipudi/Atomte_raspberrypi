# Raspberry Pi Python script using Bleak
import asyncio
from bleak import BleakServer, BleakClient, BleakGATTCharacteristic
from bleak.backends.characteristic import CharacteristicProperties
from bleak.backends.service import BleakGATTServiceCollection
import logging
import struct

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define UUIDs for service and characteristic
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef1"

class BLEServer:
    def __init__(self):
        self.data_received_callback = None
        self.connected_clients = set()

    async def handle_read(self, characteristic: BleakGATTCharacteristic, **kwargs):
        # Handle read requests from clients
        return b"Hello from Raspberry Pi"

    async def handle_write(self, characteristic: BleakGATTCharacteristic, value: bytearray, **kwargs):
        # Handle data written by clients
        try:
            decoded_value = value.decode()
            logger.info(f"Received data: {decoded_value}")
            if self.data_received_callback:
                await self.data_received_callback(decoded_value)
        except Exception as e:
            logger.error(f"Error processing received data: {e}")

    async def handle_notify(self, characteristic: BleakGATTCharacteristic, **kwargs):
        # Handle notification subscriptions
        logger.info("Client subscribed to notifications")

    async def start(self):
        # Create service collection
        services = BleakGATTServiceCollection()
        
        # Add our service
        service = services.add_service(SERVICE_UUID)
        
        # Add characteristic to the service
        char_props = CharacteristicProperties(
            read=True,
            write=True,
            notify=True,
            write_without_response=True
        )
        
        service.add_characteristic(
            CHARACTERISTIC_UUID,
            char_props,
            b"",
            self.handle_read,
            self.handle_write,
            self.handle_notify
        )

        # Start the server
        server = BleakServer(services)
        await server.start()
        
        logger.info("BLE Server started. Waiting for connections...")
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping server...")
        finally:
            await server.stop()

    async def send_notification(self, data: str):
        # Send notification to all connected clients
        encoded_data = data.encode()
        for client in self.connected_clients:
            try:
                await client.notify(CHARACTERISTIC_UUID, encoded_data)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")

def main():
    server = BLEServer()
    
    # Example callback for received data
    async def on_data_received(data):
        logger.info(f"Processing received data: {data}")
        # Send a response back
        await server.send_notification(f"Processed: {data}")
    
    server.data_received_callback = on_data_received
    
    # Run the server
    asyncio.run(server.start())

if __name__ == "__main__":
    main()


