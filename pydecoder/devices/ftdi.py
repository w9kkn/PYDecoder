"""FTDI device handling for PYDecoder."""
from typing import List, Optional

import logging
import pyftdi.ftdi
from pyftdi.gpio import GpioMpsseController

logger = logging.getLogger(__name__)

class FTDIDeviceManager:
    """Manager for FTDI devices.
    
    This class discovers, configures, and manages FTDI devices for BCD output.
    It handles up to three FTDI C232HM-EDHSL-0 devices, writing the same BCD
    value to all connected devices.
    """
    
    def __init__(self) -> None:
        """Initialize FTDI device manager.
        
        Discovers and configures available FTDI devices.
        Sets up gpio controllers for up to three devices.
        """
        self.gpio_device1: Optional[GpioMpsseController] = None
        self.gpio_device2: Optional[GpioMpsseController] = None 
        self.gpio_device3: Optional[GpioMpsseController] = None
        self.device_urls: List[str] = []
        self.device_count: int = 0
        self._discover_devices()
        self._configure_devices()
    
    def _discover_devices(self) -> None:
        """Discover connected FTDI devices."""
        try:
            self.gpio_device1 = GpioMpsseController()
            self.gpio_device2 = GpioMpsseController()
            self.gpio_device3 = GpioMpsseController()
            
            gpio_devices = pyftdi.ftdi.Ftdi.list_devices()
            
            for device_idx in range(len(gpio_devices)):
                if gpio_devices[device_idx][0][6] == "C232HM-EDHSL-0":
                    self.device_urls.append(f"ftdi://ftdi:232h:{str(gpio_devices[device_idx][0][4])}/1")
            
            self.device_count = len(self.device_urls)
            logger.info(f"Discovered {self.device_count} FTDI devices")
        except pyftdi.ftdi.FtdiError as e:
            logger.error(f"FTDI driver error discovering devices: {e}")
        except ImportError as e:
            logger.error(f"Missing FTDI driver dependency: {e}")
        except ValueError as e:
            logger.error(f"Invalid value during FTDI device discovery: {e}")
        except OSError as e:
            logger.error(f"OS error accessing FTDI devices: {e}")
        except IndexError as e:
            logger.error(f"Index error processing FTDI device list: {e}")
        except Exception as e:
            logger.error(f"Unexpected error discovering FTDI devices: {e}")
    
    def _configure_devices(self) -> None:
        """Configure discovered FTDI devices."""
        for device_idx, url in enumerate(self.device_urls):
            try:
                if device_idx == 0 and self.gpio_device1:
                    logger.debug(f"Configuring FTDI device 1: {url}")
                    self.gpio_device1.configure(
                        url, 
                        direction=(0xFF & ((1 << 8) - 1)), 
                        frequency=1e3, 
                        initial=0x0
                    )
                elif device_idx == 1 and self.gpio_device2:
                    logger.debug(f"Configuring FTDI device 2: {url}")
                    self.gpio_device2.configure(
                        url, 
                        direction=(0xFF & ((1 << 8) - 1)), 
                        frequency=1e3, 
                        initial=0x0
                    )
                elif device_idx == 2 and self.gpio_device3:
                    logger.debug(f"Configuring FTDI device 3: {url}")
                    self.gpio_device3.configure(
                        url, 
                        direction=(0xFF & ((1 << 8) - 1)), 
                        frequency=1e3, 
                        initial=0x0
                    )
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error configuring {url}: {e}")
            except ValueError as e:
                logger.error(f"Invalid parameter configuring {url}: {e}")
            except IndexError as e:
                logger.error(f"Index error configuring {url}: {e}")
            except OSError as e:
                logger.error(f"OS error configuring {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error configuring {url}: {e}")
    
    def write_bcd(self, bcd_value: int) -> None:
        """Write BCD value to all configured FTDI devices.
        
        Args:
            bcd_value: BCD value to write to devices
        """
        # Validate bcd_value is in valid range
        if not 0 <= bcd_value <= 255:
            logger.warning(f"BCD value {bcd_value} out of range (0-255), clamping")
            bcd_value = max(0, min(bcd_value, 255))
            
        # Write to each device with individual error handling
        if self.device_count > 0 and self.gpio_device1:
            try:
                self.gpio_device1.write(bcd_value)
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 1: {e}")
            except OSError as e:
                logger.error(f"OS error writing to device 1: {e}")
            except Exception as e:
                logger.error(f"Unexpected error writing to device 1: {e}")
                
        if self.device_count > 1 and self.gpio_device2:
            try:
                self.gpio_device2.write(bcd_value)
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 2: {e}")
            except OSError as e:
                logger.error(f"OS error writing to device 2: {e}")
            except Exception as e:
                logger.error(f"Unexpected error writing to device 2: {e}")
                
        if self.device_count > 2 and self.gpio_device3:
            try:
                self.gpio_device3.write(bcd_value)
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 3: {e}")
            except OSError as e:
                logger.error(f"OS error writing to device 3: {e}")
            except Exception as e:
                logger.error(f"Unexpected error writing to device 3: {e}")
    
    def close(self) -> None:
        """Close all FTDI devices and release resources.
        
        This method should be called when the application is shutting down
        to ensure proper cleanup of FTDI resources.
        """
        devices = [
            (1, self.gpio_device1),
            (2, self.gpio_device2),
            (3, self.gpio_device3)
        ]
        
        for device_num, gpio in devices:
            if gpio:
                try:
                    logger.info(f"Closing FTDI device {device_num}")
                    gpio.close()
                except pyftdi.ftdi.FtdiError as e:
                    logger.error(f"Error closing FTDI device {device_num}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error closing FTDI device {device_num}: {e}")
    
    def get_device_urls(self) -> List[str]:
        """Get list of discovered device URLs.
        
        Returns:
            List[str]: A list of FTDI device URLs that were discovered during initialization.
                       These URLs can be used to identify and reference the physical devices.
        """
        return self.device_urls