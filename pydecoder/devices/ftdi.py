"""FTDI device handling for PYDecoder."""
from typing import List, Optional

import logging
import os
import sys
import pyftdi.ftdi
from pyftdi.gpio import GpioMpsseController

logger = logging.getLogger(__name__)

# Check if backend was already selected in main.py
if sys.platform == 'win32':
    backend = os.environ.get('PYFTDI_BACKEND', '')
    if backend == 'ftd2xx':
        logger.debug("Using ftd2xx backend as configured in main.py")
    else:
        # Always ensure we're using ftd2xx on Windows
        try:
            import ftd2xx
            logger.debug("Successfully imported ftd2xx driver")
            os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
            logger.info("Using ftd2xx backend on Windows")
        except ImportError:
            logger.error("ftd2xx driver not available on Windows. It is required for this application.")
            logger.error("Please install ftd2xx package with: pip install ftd2xx")
            # We'll still set the backend to ftd2xx even though it's not available
            # This ensures we don't try to use libusb
            os.environ['PYFTDI_BACKEND'] = 'ftd2xx'

class FTDIDeviceManager:
    """Manager for FTDI devices.
    
    This class discovers, configures, and manages FTDI devices for BCD output.
    It handles up to three FTDI C232HM-EDHSL-0 devices, writing the same BCD
    value to all connected devices.
    
    In case of driver issues, it can also run in "simulation mode" where it logs
    BCD output but doesn't attempt to use actual hardware.
    """
    
    def __init__(self, simulation_mode: bool = False) -> None:
        """Initialize FTDI device manager.
        
        Discovers and configures available FTDI devices.
        Sets up gpio controllers for up to three devices.
        
        Args:
            simulation_mode: If True, runs in simulation mode without accessing hardware
        """
        self.gpio_device1: Optional[GpioMpsseController] = None
        self.gpio_device2: Optional[GpioMpsseController] = None 
        self.gpio_device3: Optional[GpioMpsseController] = None
        self.device_urls: List[str] = []
        self.device_count: int = 0
        self.simulation_mode = simulation_mode
        # Store device serials to bridge the gap between detection methods
        self.detected_serials: dict = {}
        
        # Check if we should use simulation mode
        if sys.platform == 'win32' and not simulation_mode:
            # Check if ftd2xx is available and working
            has_backend = False
            
            try:
                import ftd2xx
                # Try to check if ftd2xx is functional by listing devices
                try:
                    device_count = ftd2xx.createDeviceInfoList()
                    if device_count >= 0:  # Valid response, even if 0 devices
                        has_backend = True
                        logger.debug(f"ftd2xx is functional, found {device_count} devices")
                except Exception as e:
                    logger.warning(f"ftd2xx available but not functional: {e}")
            except ImportError:
                logger.warning("ftd2xx not available on Windows")
                
            # If ftd2xx is not available or not working, switch to simulation mode
            if not has_backend:
                logger.warning("No working ftd2xx backend found on Windows. Switching to simulation mode.")
                self.simulation_mode = True
        
        if not self.simulation_mode:
            self._discover_devices()
            self._configure_devices()
        else:
            logger.info("FTDI Device Manager running in simulation mode. BCD values will be logged but not sent to hardware.")
            # Create a simulated device for testing
            self.device_urls.append("ftdi://simulation:232h:SIM00001/1")
            self.device_count = 1
    
    def _discover_devices(self) -> None:
        """Discover connected FTDI devices using only ftd2xx."""
        try:
            self.gpio_device1 = GpioMpsseController()
            self.gpio_device2 = GpioMpsseController()
            self.gpio_device3 = GpioMpsseController()
            
            # Log which backend we're using
            backend = os.environ.get('PYFTDI_BACKEND', 'default')
            logger.debug(f"FTDI device discovery using {backend} backend")
            
            # Debug: log current backend
            logger.debug(f"Using PyFTDI backend: {backend}")
            
            # For ftd2xx backend, we don't use pyftdi's device listing
            
            # Use only ftd2xx for device detection
            try:
                logger.info("Detecting FTDI devices using only ftd2xx - VERBOSE DEBUG")
                import ftd2xx  # Import directly within this scope
                device_count = ftd2xx.createDeviceInfoList()
                logger.info(f"DEBUG: ftd2xx reports {device_count} devices")
                
                device_found = False  # Track if we found any compatible devices
                for i in range(device_count):
                    logger.info(f"DEBUG: Processing device {i}")
                    device_info = ftd2xx.getDeviceInfoDetail(i)
                    if device_info:
                        logger.info(f"DEBUG: Raw device info for device {i}: {device_info}")
                        # Safer access to device details with fallbacks
                        try:
                            flags = device_info.get("Flags", 0)
                            device_type = device_info.get("Type", 0)
                            device_id = device_info.get("ID", 0) 
                            description = device_info.get("Description", b"Unknown")
                            serial = device_info.get("SerialNumber", None)
                            logger.info(f"DEBUG: Accessed device details using get() method")
                        except AttributeError:
                            # Handle dict-like objects differently
                            logger.info(f"DEBUG: AttributeError with get(), trying dict access")
                            flags = device_info["Flags"] if "Flags" in device_info else 0
                            device_type = device_info["Type"] if "Type" in device_info else 0
                            device_id = device_info["ID"] if "ID" in device_info else 0
                            description = device_info["Description"] if "Description" in device_info else b"Unknown"
                            serial = device_info["SerialNumber"] if "SerialNumber" in device_info else None
                        logger.info(f"DEBUG: Found device: Type: {device_type}, ID: {device_id}, Description: {description}, Serial: {serial}")
                        
                        # Safely access attributes that might be missing
                        serial_str = serial.decode() if serial else f"UNKNOWN{i}"
                        logger.info(f"DEBUG: Serial string: {serial_str}")
                        
                        # Store device info keyed by product ID for later use (0x6014 = FT232H)
                        if device_type == 8 or (description and b"232H" in description):  # FT232H
                            logger.info(f"DEBUG: Device {i} is FT232H type")
                            product_id = 0x6014
                            self.detected_serials[product_id] = serial_str
                            logger.info(f"DEBUG: Stored serial for FT232H device: {serial_str}")
                            
                            # Only add the FTDI 232H devices
                            device_url = f"ftdi://ftdi:232h:{serial_str}/1"
                            logger.info(f"Found compatible FTDI device via ftd2xx: {device_url}")
                            self.device_urls.append(device_url)
                            device_found = True
                            logger.info(f"DEBUG: Added device to device_urls, current count: {len(self.device_urls)}")
                        elif device_type == 5 or (description and b"232R" in description):  # FT232R
                            logger.info(f"DEBUG: Device {i} is FT232R type (not compatible)")
                            product_id = 0x6001
                            self.detected_serials[product_id] = serial_str
                            logger.info(f"DEBUG: Stored serial for FT232R device: {serial_str}")
                    else:
                        logger.info(f"DEBUG: No device info returned for device {i}")
                
                if not device_found:
                    logger.warning(f"DEBUG: No compatible FT232H devices found despite having {device_count} FTDI devices")
                
                logger.info(f"DEBUG: Final device_urls list: {self.device_urls}")
                
            except Exception as e:
                logger.error(f"ftd2xx device detection failed: {e}")
                # If ftd2xx detection fails, we don't have any fallback - this is critical
                logger.error("No devices could be detected via ftd2xx. Device detection failed.")
                
            # Report on device discovery results
            if not self.device_urls:
                logger.warning("No FTDI devices discovered using ftd2xx. Check device connections and driver installation.")
            
            self.device_count = len(self.device_urls)
            logger.info(f"Discovered {self.device_count} FTDI devices")
            
            if self.device_count == 0:
                logger.warning("No compatible FTDI devices found. Please check device connection and driver installation.")
                logger.warning("Device detection requires FTDI C232HM-EDHSL-0 device or compatible.")
                
        except pyftdi.ftdi.FtdiError as e:
            logger.error(f"FTDI driver error discovering devices: {e}")
            if self.simulation_mode:
                logger.info("Already in simulation mode, continuing with virtual device")
            else:
                logger.warning("FTDI driver error, switching to simulation mode")
                self.simulation_mode = True
                # Create a simulated device for testing
                self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                self.device_count = 1
        except ImportError as e:
            logger.error(f"Missing FTDI driver dependency: {e}")
            if not self.simulation_mode:
                logger.warning("Missing driver dependency, switching to simulation mode")
                self.simulation_mode = True
                self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                self.device_count = 1
        except ValueError as e:
            if "already registered" in str(e).lower():
                logger.warning(f"Vendor/product registration issue: {e}")
                # This is not a fatal error, continue with discovery
            else:
                logger.error(f"Invalid value during FTDI device discovery: {e}")
                if not self.simulation_mode:
                    logger.warning("Value error during device discovery, switching to simulation mode")
                    self.simulation_mode = True
                    self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                    self.device_count = 1
        except OSError as e:
            logger.error(f"OS error accessing FTDI devices: {e}")
            if not self.simulation_mode:
                logger.warning("OS error accessing devices, switching to simulation mode")
                self.simulation_mode = True
                self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                self.device_count = 1
        except IndexError as e:
            logger.error(f"Index error processing FTDI device list: {e}")
            if not self.simulation_mode:
                logger.warning("Error processing device list, switching to simulation mode")
                self.simulation_mode = True
                self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                self.device_count = 1
        except Exception as e:
            logger.error(f"Unexpected error discovering FTDI devices: {e}", exc_info=True)
            if not self.simulation_mode:
                logger.warning("Unexpected error during device discovery, switching to simulation mode")
                self.simulation_mode = True
                self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                self.device_count = 1
    
    def _configure_devices(self) -> None:
        """Configure discovered FTDI devices."""
        # Log the device URLs we have at this point
        logger.info(f"DEBUG: Configure devices - device URLs at start: {self.device_urls}")
        
        # For Windows, we need special handling for ftd2xx
        import sys
        windows_ftd2xx_mode = sys.platform == 'win32' and os.environ.get('PYFTDI_BACKEND') == 'ftd2xx'
        logger.info(f"DEBUG: Windows ftd2xx mode: {windows_ftd2xx_mode}")
        
        for device_idx, url in enumerate(self.device_urls):
            try:
                # Special handling for Windows with ftd2xx backend
                if windows_ftd2xx_mode:
                    logger.info(f"Using Windows-specific configuration approach for {url}")
                    
                    # For Windows, we need to properly initialize GpioMpsseController
                    try:
                        # Check if we need to try an alternative approach with direct device URL
                        if "UNKNOWN" in url:
                            # If we have an UNKNOWN serial, try with first available device instead
                            logger.debug("Device has unknown serial number, trying with interface 1")
                            url = "ftdi://ftdi:232h/1"  # Use first available device
                            
                        # Properly configure the existing GpioMpsseController instance
                        if device_idx == 0 and self.gpio_device1:
                            logger.debug(f"Configuring FTDI device 1 with Windows-specific approach: {url}")
                            try:
                                # Create a new controller to avoid issues with previous configuration attempts
                                self.gpio_device1 = GpioMpsseController()
                                
                                # Use simpler configuration approach
                                self.gpio_device1.configure(
                                    url, 
                                    direction=0xFF,  # All pins as outputs
                                    frequency=1e3,   # 1 kHz
                                    initial=0x0      # Initial value 0
                                )
                                logger.info(f"Successfully configured device 1 with MPSSE mode")
                            except Exception as e:
                                logger.error(f"Error configuring device 1: {e}")
                                # Fall back to simulation for this device
                                self.gpio_device1 = None
                        elif device_idx == 1 and self.gpio_device2:
                            logger.debug(f"Configuring FTDI device 2 with Windows-specific approach: {url}")
                            try:
                                # Create a new controller
                                self.gpio_device2 = GpioMpsseController()
                                
                                self.gpio_device2.configure(
                                    url, 
                                    direction=0xFF,  # All pins as outputs
                                    frequency=1e3,   # 1 kHz
                                    initial=0x0      # Initial value 0
                                )
                                logger.info(f"Successfully configured device 2 with MPSSE mode")
                            except Exception as e:
                                logger.error(f"Error configuring device 2: {e}")
                                # Fall back to simulation for this device
                                self.gpio_device2 = None
                        elif device_idx == 2 and self.gpio_device3:
                            logger.debug(f"Configuring FTDI device 3 with Windows-specific approach: {url}")
                            try:
                                # Create a new controller
                                self.gpio_device3 = GpioMpsseController()
                                
                                self.gpio_device3.configure(
                                    url, 
                                    direction=0xFF,  # All pins as outputs
                                    frequency=1e3,   # 1 kHz
                                    initial=0x0      # Initial value 0
                                )
                                logger.info(f"Successfully configured device 3 with MPSSE mode")
                            except Exception as e:
                                logger.error(f"Error configuring device 3: {e}")
                                # Fall back to simulation for this device
                                self.gpio_device3 = None
                                
                        # Continue to next device
                        continue
                        
                    except ImportError as e:
                        logger.error(f"Failed to import necessary module for device access: {e}")
                    except Exception as e:
                        logger.error(f"Error in Windows-specific device configuration: {e}")
                
                # Standard configuration approach
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
                if "Operation not supported" in str(e) and sys.platform == 'win32':
                    logger.warning(f"Windows USB access limitation detected: {e}")
                    logger.warning("This is likely due to Windows USB driver restrictions. Try running as Administrator.")
                    logger.warning("Falling back to simulation mode")
                    self.simulation_mode = True
                    # Add a simulated device for testing
                    self.device_urls = ["ftdi://simulation:232h:SIM00001/1"]
                    self.device_count = 1
                    break
                else:
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
            
        # In simulation mode, just log the BCD value and return
        if self.simulation_mode:
            logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
            return
        
        # Check for Windows - we need special handling for ftd2xx backend
        import sys
        windows_ftd2xx_mode = sys.platform == 'win32' and os.environ.get('PYFTDI_BACKEND') == 'ftd2xx'
        
        # For Windows, use appropriate handling for ftd2xx backend
        if windows_ftd2xx_mode:
            devices = [
                (1, self.gpio_device1),
                (2, self.gpio_device2),
                (3, self.gpio_device3)
            ]
            
            for device_num, gpio in devices:
                if gpio:
                    try:
                        # Use standard GPIO write method which handles MPSSE internally
                        gpio.write(bcd_value)
                        logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device {device_num} on Windows")
                    except Exception as e:
                        logger.error(f"Error writing to FTDI device {device_num} on Windows: {e}")
                        # If write fails, fall back to simulation mode
                        logger.warning(f"FTDI write failed on Windows, switching to simulation mode")
                        self.simulation_mode = True
                        break
            
            # If we've switched to simulation mode, return after logging
            if self.simulation_mode:
                logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
                return
            
            # If we successfully wrote via standard method, we're done
            return
            
        # Standard GPIO write for non-Windows or ftd2xx backend
        # Write to each device with individual error handling
        if self.device_count > 0 and self.gpio_device1:
            try:
                self.gpio_device1.write(bcd_value)
                logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 1")
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 1: {e}")
                # If we see "Operation not supported" on Windows, switch to simulation
                if "Operation not supported" in str(e) and sys.platform == 'win32':
                    logger.warning("Windows USB access limitation detected. Switching to simulation mode.")
                    self.simulation_mode = True
                    # Log the simulated write
                    logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
                    return
            except OSError as e:
                logger.error(f"OS error writing to device 1: {e}")
            except Exception as e:
                logger.error(f"Unexpected error writing to device 1: {e}")
                
        if self.device_count > 1 and self.gpio_device2:
            try:
                self.gpio_device2.write(bcd_value)
                logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 2")
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 2: {e}")
            except OSError as e:
                logger.error(f"OS error writing to device 2: {e}")
            except Exception as e:
                logger.error(f"Unexpected error writing to device 2: {e}")
                
        if self.device_count > 2 and self.gpio_device3:
            try:
                self.gpio_device3.write(bcd_value)
                logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 3")
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
        # In simulation mode, just log and return
        if self.simulation_mode:
            logger.info("SIMULATION: Closing simulated FTDI devices")
            return
            
        # Check for Windows with ftd2xx - we need special handling
        import sys
        windows_ftd2xx_mode = sys.platform == 'win32' and os.environ.get('PYFTDI_BACKEND') == 'ftd2xx'
        
        devices = [
            (1, self.gpio_device1),
            (2, self.gpio_device2),
            (3, self.gpio_device3)
        ]
        
        for device_num, gpio in devices:
            if gpio:
                try:
                    # Use standard close for Windows with ftd2xx backend
                    # GpioMpsseController.close() will handle closing the underlying FTDI device
                    logger.info(f"Closing FTDI device {device_num}")
                    gpio.close()
                except pyftdi.ftdi.FtdiError as e:
                    if "Operation not supported" in str(e) and sys.platform == 'win32':
                        logger.warning(f"Windows USB access limitation detected while closing device {device_num}: {e}")
                    else:
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