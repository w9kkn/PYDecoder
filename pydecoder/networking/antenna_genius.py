"""Module for communicating with 4O3A Antenna Genius devices."""
import logging
import socket
from typing import Tuple, Optional, Callable

logger = logging.getLogger(__name__)

class AntennaGenius:
    """Client for communicating with 4O3A Antenna Genius devices.
    
    This class handles the TCP communication with an Antenna Genius device
    for setting antenna ports based on the current radio frequency.
    It uses a callback mechanism to report status back to the UI.
    """
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None) -> None:
        """Initialize AntennaGenius client.
        
        Args:
            status_callback: Optional callback function to receive status messages.
                             This function is called with status updates that can be
                             displayed in the UI.
        """
        self.status_callback = status_callback
    
    def set_antenna(self, ip_address: str, tcp_port: int, radio_nr: str, antenna_port: int) -> bool:
        """Send antenna selection command to AntennaGenius.
        
        Args:
            ip_address: IP address of the AntennaGenius device
            tcp_port: TCP port of the AntennaGenius device
            radio_nr: Radio number to configure
            antenna_port: Antenna port to select
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        # Format the command string
        # Example: "C0|port set 1 band=2"
        command_str = f"C1|port set {radio_nr} band={antenna_port} \n"

        try:
            # Using context manager to ensure socket is properly closed
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)  # Timeout after 0.5 seconds
                sock.connect((ip_address, tcp_port))
                sock.sendall(bytes(command_str, 'utf-8'))
                
            if self.status_callback:
                self.status_callback("AG Message Delivered!")
            logger.debug(f"AntennaGenius command sent successfully: {command_str.strip()}")
            return True
                
        except socket.gaierror as e:
            error_msg = f"AntennaGenius address error: {ip_address}:{tcp_port} - {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Address error")
            logger.error(error_msg)
            return False
        except socket.timeout as e:
            error_msg = f"AntennaGenius connection timeout: {ip_address}:{tcp_port} - {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Connection timeout")
            logger.error(error_msg)
            return False
        except ConnectionRefusedError as e:
            error_msg = f"AntennaGenius connection refused: {ip_address}:{tcp_port} - {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Connection refused")
            logger.error(error_msg)
            return False
        except socket.error as e:
            error_msg = f"AntennaGenius socket error: {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Socket error")
            logger.error(error_msg)
            return False
        except OSError as e:
            error_msg = f"AntennaGenius OS error: {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! OS error")
            logger.error(error_msg)
            return False