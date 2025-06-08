"""Module for communicating with 4O3A Antenna Genius devices."""
import logging
import socket
import time
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
        self.socket = None
        self.command_counter = 0
        self.last_connection_time = 0
        self.connection_address = None
    
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
        # Increment command counter and wrap around at 100
        self.command_counter = (self.command_counter + 1) % 100
        
        # Format the command string with incrementing counter
        # Example: "C42|port set 1 band=2"
        command_str = f"C{self.command_counter}|port set {radio_nr} band={antenna_port} \n"

        try:
            # Check if we need to reconnect (different address or stale connection)
            current_address = (ip_address, tcp_port)
            current_time = time.time()
            
            # Close existing socket if:
            # 1. Connection is to a different address
            # 2. Connection is older than 30 seconds (prevent stale connections)
            # 3. Socket exists but might be in a bad state
            should_reconnect = (
                self.socket is None or
                self.connection_address != current_address or
                (current_time - self.last_connection_time) > 30
            )
            
            if should_reconnect and self.socket is not None:
                logger.debug("Closing existing socket before reconnecting")
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None
            
            # Create new connection if needed
            if self.socket is None:
                logger.debug(f"Creating new connection to {ip_address}:{tcp_port}")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(0.5)  # Quick timeout for LAN operations
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # Enable TCP keepalive
                self.socket.connect((ip_address, tcp_port))
                self.connection_address = current_address
                self.last_connection_time = current_time
                
            # Send command with timeout
            self.socket.settimeout(0.5)  # Quick timeout for LAN operations
            self.socket.sendall(bytes(command_str, 'utf-8'))
                
            if self.status_callback:
                self.status_callback("AG Message Delivered!")
            logger.debug(f"AntennaGenius command sent successfully: {command_str.strip()}")
            return True
                
        except socket.gaierror as e:
            error_msg = f"AntennaGenius address error: {ip_address}:{tcp_port} - {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Address error")
            logger.error(error_msg)
            self.socket = None  # Reset socket on error
            return False
        except socket.timeout as e:
            error_msg = f"AntennaGenius connection timeout: {ip_address}:{tcp_port} - {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Connection timeout")
            logger.error(error_msg)
            self.socket = None  # Reset socket on error
            return False
        except ConnectionRefusedError as e:
            error_msg = f"AntennaGenius connection refused: {ip_address}:{tcp_port} - {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Connection refused")
            logger.error(error_msg)
            self.socket = None  # Reset socket on error
            return False
        except socket.error as e:
            error_msg = f"AntennaGenius socket error: {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! Socket error")
            logger.error(error_msg)
            self.socket = None  # Reset socket on error
            return False
        except OSError as e:
            error_msg = f"AntennaGenius OS error: {e}"
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! OS error")
            logger.error(error_msg)
            self.socket = None  # Reset socket on error
            return False
            
    def close(self) -> None:
        """Close the socket connection."""
        if self.socket is not None:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing AntennaGenius socket: {e}")
            finally:
                self.socket = None