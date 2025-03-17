"""Module for interacting with N1MM+ UDP broadcasts."""
import json
import logging
import socket
import xmltodict
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class N1MMListener:
    """Listener for N1MM+ UDP broadcasts.
    
    This class sets up a UDP socket to listen for XML broadcasts from N1MM+ logger.
    It parses these broadcasts to extract radio frequency information that can
    be used to control antenna switching and band-pass filters.
    """
    
    def __init__(self) -> None:
        """Initialize N1MM listener.
        
        Creates an instance with no active socket. The socket will be
        created when setup_socket() is called.
        """
        self.sock: Optional[socket.socket] = None
    
    def setup_socket(self, ip_address: str, udp_port: int) -> bool:
        """Set up UDP socket for listening.
        
        Args:
            ip_address: IP address to bind to
            udp_port: UDP port to bind to
            
        Returns:
            bool: True if socket was set up successfully, False otherwise
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(5)  # 5 second timeout
            self.sock.bind((ip_address, udp_port))
            return True
        except socket.gaierror as e:
            logger.error(f"Invalid address: {ip_address}:{udp_port} - {e}")
            return False
        except socket.error as e:
            logger.error(f"Socket error setting up N1MM listener: {e}")
            return False
        except OSError as e:
            logger.error(f"OS error setting up N1MM socket: {e}")
            return False
    
    def receive_data(self) -> Optional[Dict[str, Any]]:
        """Receive and parse data from N1MM+.
        
        Returns:
            Optional[Dict]: Parsed radio data or None if error occurred
        """
        if not self.sock:
            logger.warning("Attempted to receive data with no socket initialized")
            return None
            
        try:
            data, addr = self.sock.recvfrom(2048)
            xml_str = data.decode("utf-8")
            radio_dict = json.loads(json.dumps(xmltodict.parse(xml_str)))
            return radio_dict
        except socket.timeout:
            # This is normal, just no data received
            return None
        except socket.error as e:
            logger.error(f"Socket error receiving data from N1MM: {e}")
            return None
        except UnicodeDecodeError as e:
            logger.error(f"Decode error (invalid UTF-8) from N1MM: {e}")
            return None
        except xmltodict.expat.ExpatError as e:
            logger.error(f"XML parsing error from N1MM data: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON conversion error from N1MM data: {e}")
            return None
        except ValueError as e:
            logger.error(f"Value error processing N1MM data: {e}")
            return None
    
    def close(self) -> None:
        """Close socket and release resources.
        
        This method should be called when the application is shutting down
        to ensure proper cleanup of network resources.
        """
        if self.sock:
            try:
                # Unregister from select if it's being used in a polling loop
                self.sock.setblocking(True)
                # Close the socket
                self.sock.close()
                logger.debug("N1MM socket closed successfully")
            except socket.error as e:
                logger.error(f"Socket error closing N1MM socket: {e}")
            except OSError as e:
                logger.error(f"OS error closing N1MM socket: {e}")
            finally:
                # Always set to None to prevent further usage attempts
                self.sock = None