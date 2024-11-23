import bluetooth,logging

def setup_logger():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
logger = setup_logger()

# Create a Bluetooth socket
server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

# Bind the socket to a port
port = 1
server_socket.bind(("", port))
server_socket.listen(1)

logger.info("Waiting for a connection...")

# Accept an incoming connection
client_socket, address = server_socket.accept()
logger.info(f"Connected to {address}")

try:
    while True:

        data = client_socket.recv(1024)
        if not data:
            break
        logger.info(f"Received: {data.decode('utf-8')}")
except Exception as e:
    logger.error(f"Error: {e}")
finally:
    client_socket.close()
    server_socket.close()

