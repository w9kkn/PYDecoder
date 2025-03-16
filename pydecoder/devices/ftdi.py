"""FTDI device handling for PYDecoder."""
from typing import List, Optional

import pyftdi
from pyftdi.gpio import GpioMpsseController

class FTDIDeviceManager:
    """Manager for FTDI devices."""
    
    def __init__(self):
        """Initialize FTDI device manager."""
        self.gpio1: Optional[GpioMpsseController] = None
        self.gpio2: Optional[GpioMpsseController] = None 
        self.gpio3: Optional[GpioMpsseController] = None
        self.device_urls: List[str] = []
        self.device_count: int = 0
        self._discover_devices()
        self._configure_devices()
    
    def _discover_devices(self) -> None:
        """Discover connected FTDI devices."""
        try:
            self.gpio1 = GpioMpsseController()
            self.gpio2 = GpioMpsseController()
            self.gpio3 = GpioMpsseController()
            
            gpios = pyftdi.ftdi.Ftdi.list_devices()
            
            for device in range(len(gpios)):
                if gpios[device][0][6] == "C232HM-EDHSL-0":
                    self.device_urls.append(f"ftdi://ftdi:232h:{str(gpios[device][0][4])}/1")
            
            self.device_count = len(self.device_urls)
        except Exception as e:
            print(f"Error discovering FTDI devices: {e}")
    
    def _configure_devices(self) -> None:
        """Configure discovered FTDI devices."""
        try:
            if self.device_count > 0 and self.gpio1:
                self.gpio1.configure(
                    self.device_urls[0], 
                    direction=(0xFF & ((1 << 8) - 1)), 
                    frequency=1e3, 
                    initial=0x0
                )
            if self.device_count > 1 and self.gpio2:
                self.gpio2.configure(
                    self.device_urls[1], 
                    direction=(0xFF & ((1 << 8) - 1)), 
                    frequency=1e3, 
                    initial=0x0
                )
            if self.device_count > 2 and self.gpio3:
                self.gpio3.configure(
                    self.device_urls[2], 
                    direction=(0xFF & ((1 << 8) - 1)), 
                    frequency=1e3, 
                    initial=0x0
                )
        except Exception as e:
            print(f"Error configuring FTDI devices: {e}")
    
    def write_bcd(self, bcd_value: int) -> None:
        """Write BCD value to all configured FTDI devices.
        
        Args:
            bcd_value: BCD value to write to devices
        """
        try:
            if self.device_count > 0 and self.gpio1:
                self.gpio1.write(bcd_value)
            if self.device_count > 1 and self.gpio2:
                self.gpio2.write(bcd_value)
            if self.device_count > 2 and self.gpio3:
                self.gpio3.write(bcd_value)
        except Exception as e:
            print(f"Error writing to FTDI devices: {e}")
    
    def get_device_urls(self) -> List[str]:
        """Get list of discovered device URLs."""
        return self.device_urls