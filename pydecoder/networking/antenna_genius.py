"""Module for communicating with 4O3A Antenna Genius devices."""
import socket
from typing import Tuple, Optional, Callable

class AntennaGenius:
    """Client for communicating with 4O3A Antenna Genius devices."""
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
        """Initialize AntennaGenius client.
        
        Args:
            status_callback: Optional callback function to receive status messages
        """
        self.status_callback = status_callback
    
    def set_antenna(self, ipaddr: str, tcp_port: int, radio_nr: str, ant_port: int) -> bool:
        """Send antenna selection command to AntennaGenius.
        
        Args:
            ipaddr: IP address of the AntennaGenius device
            tcp_port: TCP port of the AntennaGenius device
            radio_nr: Radio number to configure
            ant_port: Antenna port to select
            
        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        # old version:
        # tcp_str = f"!000a!00cc80!{radio_nr};{ant_port}\n"
        # new version
        # C0|port set 1 band=2
        tcp_str = f"C0|port set {radio_nr} band={ant_port}\n"

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)  # Timeout after 0.5 seconds
                s.connect((ipaddr, tcp_port))
                s.sendall(bytes(tcp_str, 'utf-8'))
                
            if self.status_callback:
                self.status_callback("AG Message Delivered!")
            return True
                
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"AG Comm Failure! {str(e)}")
            return False