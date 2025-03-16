"""Module for interacting with N1MM+ UDP broadcasts."""
import json
import socket
import xmltodict
from typing import Dict, Any, Optional, Tuple

class N1MMListener:
    """Listener for N1MM+ UDP broadcasts."""
    
    def __init__(self):
        """Initialize N1MM listener."""
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
        except Exception as e:
            print(f"Error setting up N1MM socket: {e}")
            return False
    
    def receive_data(self) -> Optional[Dict[str, Any]]:
        """Receive and parse data from N1MM+.
        
        Returns:
            Optional[Dict]: Parsed radio data or None if error occurred
        """
        if not self.sock:
            return None
            
        try:
            data, addr = self.sock.recvfrom(2048)
            xml_str = data.decode("utf-8")
            radio_dict = json.loads(json.dumps(xmltodict.parse(xml_str)))
            return radio_dict
        except socket.timeout:
            # This is normal, just no data received
            return None
        except Exception as e:
            print(f"Error receiving data from N1MM: {e}")
            return None
    
    def close(self) -> None:
        """Close socket."""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                print(f"Error closing N1MM socket: {e}")
            finally:
                self.sock = None