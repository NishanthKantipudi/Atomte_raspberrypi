import usb.core
import usb.util
import time
import logging
from typing import Optional, Tuple
from contextlib import contextmanager

class RobustUSBHandler:
    def __init__(self, vendor_id: int = 0x18d1, product_id: int = 0x4ee7,
                 timeout: int = 1000, retry_attempts: int = 3):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.device = None
        self.ep_out = None
        self.ep_in = None
        self.logger = logging.getLogger('USBHandler')
        
        # Configure logging
        self.logger.setLevel(logging.DEBUG)
        
    def connect(self) -> bool:
        """Establish connection with retry mechanism"""
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Looking for device with ID {hex(self.vendor_id)}:{hex(self.product_id)}")
                self.device = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
                
                if self.device is None:
                    raise usb.core.USBError("Device not found")
                
                self.logger.debug("Device found")
                
                # Handle kernel driver
                if self.device.is_kernel_driver_active(0):
                    self.logger.debug("Detaching kernel driver")
                    self.device.detach_kernel_driver(0)
                
                # Set configuration
                self.device.set_configuration()
                self.logger.debug("Configuration set")
                
                # Find endpoints
                cfg = self.device.get_active_configuration()
                intf = cfg[(0,0)]
                
                self.ep_out = usb.util.find_descriptor(
                    intf,
                    custom_match=lambda e: 
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                )
                
                self.ep_in = usb.util.find_descriptor(
                    intf,
                    custom_match=lambda e: 
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
                )
                
                if not all([self.ep_out, self.ep_in]):
                    raise usb.core.USBError("Could not find required endpoints")
                
                self.logger.debug(f"OUT endpoint found: {hex(self.ep_out.bEndpointAddress)}")
                self.logger.debug(f"IN endpoint found: {hex(self.ep_in.bEndpointAddress)}")
                
                return True
                
            except usb.core.USBError as e:
                self.logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(1)  # Wait before retry
                    self.reset()
                else:
                    raise
        
        return False
    
    @contextmanager
    def transaction(self):
        """Context manager for handling USB transactions"""
        try:
            yield
        except usb.core.USBError as e:
            if e.errno == 19:  # Device disconnected
                self.logger.error("Device disconnected during transaction")
                self.reset()
                raise
            elif e.errno == 5:  # I/O error
                self.logger.error("I/O error during transaction")
                # Flush endpoints
                self._flush_endpoints()
                raise
            else:
                raise
                
    def send_data(self, data: bytes, timeout: Optional[int] = None) -> int:
        """Send data with retry mechanism"""
        if not self.ep_out:
            raise RuntimeError("Device not properly initialized")
            
        with self.transaction():
            try:
                return self.ep_out.write(data, timeout=timeout or self.timeout)
            except usb.core.USBError as e:
                self.logger.error(f"Error sending data: {str(e)}")
                raise
                
    def receive_data(self, size: int = 64, timeout: Optional[int] = None) -> bytes:
        """Receive data with retry mechanism"""
        if not self.ep_in:
            raise RuntimeError("Device not properly initialized")
            
        with self.transaction():
            try:
                return self.ep_in.read(size, timeout=timeout or self.timeout)
            except usb.core.USBError as e:
                self.logger.error(f"Error receiving data: {str(e)}")
                raise
    
    def _flush_endpoints(self):
        """Flush endpoints to clear any pending data"""
        try:
            while True:
                self.ep_in.read(64, timeout=10)
        except:
            pass
            
    def reset(self):
        """Reset the USB device state"""
        if self.device:
            try:
                self.device.reset()
            except:
                pass
        self.device = None
        self.ep_out = None
        self.ep_in = None
        
    def __del__(self):
        """Cleanup resources"""
        self.reset()
        if self.device:
            usb.util.dispose_resources(self.device)

# Example usage:
if __name__ == "__main__":
    handler = RobustUSBHandler()
    try:
        handler.connect()
        
        # Example data transfer with retry
        data_to_send = b"Hello Device"
        for attempt in range(3):
            try:
                handler.send_data(data_to_send)
                response = handler.receive_data()
                break
            except usb.core.USBError as e:
                if attempt == 2:  # Last attempt
                    raise
                time.sleep(1)
                handler.connect()  # Reconnect and retry
                
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise