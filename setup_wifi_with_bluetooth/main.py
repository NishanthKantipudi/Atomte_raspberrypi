# Raspberry Pi (Python) - usb_handler.py
import usb.core
import usb.util
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('USBHandler')

class USBHandler:
    def __init__(self):
        # Google Pixel vendor ID and product ID
        self.VENDOR_ID = 0x18d1
        self.PRODUCT_ID = 0x4ee7
        
        self.device = None
        self.endpoint_in = None
        self.endpoint_out = None
        self.interface = None
        
        self.connect()

    def connect(self):
        try:
            # Find the device
            logger.debug(f"Looking for device with ID {hex(self.VENDOR_ID)}:{hex(self.PRODUCT_ID)}")
            self.device = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
            
            if self.device is None:
                raise ValueError('Device not found')

            logger.debug("Device found")

            # Set configuration
            self.device.set_configuration()
            logger.debug("Configuration set")

            # Get an endpoint instance
            cfg = self.device.get_active_configuration()
            self.interface = cfg[(0,0)]
            
            # Find endpoints
            for endpoint in self.interface:
                if endpoint.bEndpointAddress & 0x80:
                    self.endpoint_in = endpoint
                    logger.debug(f"IN endpoint found: {hex(endpoint.bEndpointAddress)}")
                else:
                    self.endpoint_out = endpoint
                    logger.debug(f"OUT endpoint found: {hex(endpoint.bEndpointAddress)}")

        except Exception as e:
            logger.error(f"Error during connection: {str(e)}")
            raise

    def send_data(self, data: str):
        try:
            if not self.device or not self.endpoint_out:
                logger.error("Device or endpoint not initialized")
                return False

            # Convert string to bytes and send
            bytes_sent = self.device.write(self.endpoint_out.bEndpointAddress, data.encode())
            logger.debug(f"Sent {bytes_sent} bytes")
            return True
        except usb.core.USBError as e:
            logger.error(f"Error sending data: {e}")
            return False

    def receive_data(self) -> str:
        try:
            if not self.device or not self.endpoint_in:
                logger.error("Device or endpoint not initialized")
                return ""

            # Read data
            data = self.device.read(self.endpoint_in.bEndpointAddress, 
                                  self.endpoint_in.wMaxPacketSize,
                                  timeout=1000)
            received = bytes(data).decode()
            logger.debug(f"Received: {received}")
            return received
        except usb.core.USBError as e:
            if e.errno == 110:  # Timeout
                logger.debug("No data available")
            else:
                logger.error(f"Error receiving data: {e}")
            return ""

    def close(self):
        try:
            # Release the device
            usb.util.dispose_resources(self.device)
            logger.debug("USB connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

# Example usage
if __name__ == "__main__":
    usb_handler = USBHandler()
    
    try:
        while True:
            # Example: Send data
            message = "Hello from Raspberry Pi!"
            if usb_handler.send_data(message):
                logger.info(f"Sent: {message}")
            
            # Example: Receive data
            received = usb_handler.receive_data()
            if received:
                logger.info(f"Received: {received}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\nClosing connection...")
        usb_handler.close()