import sys
import logging
import asyncio
import threading
from typing import Any, Union, Dict, Optional
from bless import (
    BlessServer,
    BlessGATTCharacteristic,
    GATTCharacteristicProperties,
    GATTAttributePermissions
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(name=__name__)

class BLEServer:
    def __init__(self, service_name: str = "RaspberryPi BLE Service"):
        self.service_name = service_name
        self.server: Optional[BlessServer] = None
        self.characteristics: Dict[str, BlessGATTCharacteristic] = {}
        
        # Platform-specific event trigger
        self.trigger: Union[asyncio.Event, threading.Event]
        if sys.platform in ["darwin", "win32"]:
            self.trigger = threading.Event()
        else:
            self.trigger = asyncio.Event()
        
        # Service and characteristic UUIDs
        self.service_uuid = "A07498CA-AD5B-474E-940D-16F1FBE7E8CD"
        self.char_uuid = "51FF12BB-3ED8-46E5-B4F9-D64E2FEC021B"
        
    async def setup_server(self, loop: asyncio.AbstractEventLoop):
        """Initialize and configure the BLE server"""
        self.server = BlessServer(name=self.service_name, loop=loop)
        self.server.read_request_func = self.read_request
        self.server.write_request_func = self.write_request
        
        # Add service
        await self.server.add_new_service(self.service_uuid)
        
        # Configure characteristic properties
        char_flags = (
            GATTCharacteristicProperties.read |
            GATTCharacteristicProperties.write |
            GATTCharacteristicProperties.indicate
        )
        permissions = (
            GATTAttributePermissions.readable |
            GATTAttributePermissions.writeable
        )
        
        # Add characteristic to service
        await self.server.add_new_characteristic(
            self.service_uuid,
            self.char_uuid,
            char_flags,
            None,
            permissions
        )
        
        # Store characteristic reference
        self.characteristics[self.char_uuid] = self.server.get_characteristic(self.char_uuid)
        
    def read_request(self, characteristic: BlessGATTCharacteristic, **kwargs) -> bytearray:
        """Handle read requests from connected devices"""
        logger.debug(f"Read request for {characteristic.uuid}: {characteristic.value}")
        return characteristic.value
        
    def write_request(self, characteristic: BlessGATTCharacteristic, value: Any, **kwargs):
        """Handle write requests from connected devices"""
        characteristic.value = value
        logger.debug(f"Write request: Characteristic {characteristic.uuid} value set to {value}")
        
        # Process received data
        try:
            decoded_value = value.decode() if isinstance(value, bytes) else str(value)
            self.handle_received_data(decoded_value)
        except Exception as e:
            logger.error(f"Error processing received data: {e}")
        
        # Check for special commands
        if value == b"\x0f":
            logger.debug("Received trigger command")
            self.trigger.set()
            
    def handle_received_data(self, data: str):
        """Process received data"""
        logger.info(f"Processing received data: {data}")
        # Add your custom data processing logic here
        
    async def update_characteristic(self, value: str):
        """Update characteristic value and notify connected devices"""
        if self.server and self.char_uuid in self.characteristics:
            char = self.characteristics[self.char_uuid]
            char.value = value.encode()
            self.server.update_value(self.service_uuid, self.char_uuid)
            logger.debug(f"Updated characteristic value to: {value}")
    
    async def run(self, loop: asyncio.AbstractEventLoop):
        """Main server operation loop"""
        try:
            # Clear any existing triggers
            self.trigger.clear()
            
            # Setup and start server
            await self.setup_server(loop)
            await self.server.start()
            
            logger.info("BLE Server started and advertising")
            logger.info(f"Service UUID: {self.service_uuid}")
            logger.info(f"Characteristic UUID: {self.char_uuid}")
            
            # Wait for events/commands
            if isinstance(self.trigger, threading.Event):
                self.trigger.wait()
            else:
                await self.trigger.wait()
            
            # Keep server running and handle updates
            while True:
                await asyncio.sleep(1)
                # Add any periodic tasks here
                
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up server resources"""
        if self.server:
            await self.server.stop()
            logger.info("BLE Server stopped")

async def main():
    """Main entry point"""
    server = BLEServer()
    loop = asyncio.get_event_loop()
    try:
        await server.run(loop)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())