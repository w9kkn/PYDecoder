"""FTDI device handling for PYDecoder."""
from typing import List, Optional

import logging
import os
import sys
import pyftdi.ftdi
from pyftdi.gpio import GpioMpsseController
import usb.core
import usb.util

logger = logging.getLogger(__name__)

# Try both backends on Windows
if sys.platform == 'win32':
    # Try libusb1 backend first (seems to have better device detection)
    try:
        import usb.backend.libusb1
        # Try different methods to locate the DLL
        logger.debug("Trying to find libusb1 backend")
        
        # Method 1: Check local DLL first (our preferred option)
        libusb_dll_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'libusb-1.0.dll')
        if os.path.exists(libusb_dll_path):
            logger.debug(f"Found local libusb DLL at {libusb_dll_path}")
            backend = usb.backend.libusb1.get_backend(find_library=lambda x: libusb_dll_path)
            if backend:
                logger.debug("Successfully initialized libusb1 backend with local DLL")
                os.environ['PYFTDI_BACKEND'] = 'libusb'
                logger.info("Using libusb backend on Windows (direct DLL)")
            else:
                logger.warning("Could not initialize libusb1 backend with local DLL")
        
        # Method 2: Try libusb_package
        if 'PYFTDI_BACKEND' not in os.environ:
            try:
                import libusb_package
                logger.debug("Found libusb_package module")
                backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
                if backend:
                    logger.debug("Successfully initialized libusb1 backend with libusb_package")
                    os.environ['PYFTDI_BACKEND'] = 'libusb'
                    logger.info("Using libusb backend on Windows (libusb_package)")
                else:
                    logger.warning("Could not initialize libusb1 backend with libusb_package")
            except ImportError:
                logger.warning("libusb_package module not available")
            
        # Method 3: Windows DLL path search
        if 'PYFTDI_BACKEND' not in os.environ:
            # Check common Windows DLL locations
            common_dll_paths = [
                "C:\\Windows\\System32\\libusb-1.0.dll",
                "C:\\Windows\\SysWOW64\\libusb-1.0.dll"
            ]
            for dll_path in common_dll_paths:
                if os.path.exists(dll_path):
                    logger.debug(f"Found system libusb DLL at {dll_path}")
                    backend = usb.backend.libusb1.get_backend(find_library=lambda x: dll_path)
                    if backend:
                        logger.debug(f"Successfully initialized libusb1 backend with system DLL at {dll_path}")
                        os.environ['PYFTDI_BACKEND'] = 'libusb'
                        logger.info("Using libusb backend on Windows (system DLL)")
                        break
                    else:
                        logger.warning(f"Could not initialize libusb1 backend with system DLL at {dll_path}")
    except ImportError:
        logger.warning("libusb1 backend not available on Windows")
    except Exception as e:
        logger.warning(f"Error initializing libusb1 backend: {e}")
    
    # If libusb1 failed, try ftd2xx backend
    if 'PYFTDI_BACKEND' not in os.environ:
        try:
            import ftd2xx
            logger.debug("Successfully imported ftd2xx driver")
            os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
            logger.info("Using ftd2xx backend on Windows")
        except ImportError:
            logger.warning("ftd2xx driver not available on Windows")
    
    # Log final backend status
    if 'PYFTDI_BACKEND' not in os.environ:
        logger.warning("No USB backend successfully initialized on Windows. Device detection may fail.")
        # Create a dummy environment variable so we can check if neither backend worked
        os.environ['PYFTDI_BACKEND'] = 'none'

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
        
        # Check if we should use simulation mode
        if sys.platform == 'win32' and not simulation_mode:
            # Try to detect if we have any viable backends on Windows
            has_backend = False
            
            # Check if ftd2xx is available
            try:
                import ftd2xx
                has_backend = True
            except ImportError:
                logger.warning("ftd2xx not available")
                
            # Check if libusb backend is working
            try:
                import usb.core
                import usb.backend.libusb1
                libusb_dll_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'libusb-1.0.dll')
                if os.path.exists(libusb_dll_path):
                    backend = usb.backend.libusb1.get_backend(find_library=lambda x: libusb_dll_path)
                    if backend:
                        # Try to enumerate devices to see if the backend is functional
                        devices = list(usb.core.find(find_all=True, backend=backend))
                        if devices:
                            has_backend = True
                    else:
                        logger.warning("libusb backend initialization failed")
            except Exception as e:
                logger.warning(f"Error checking libusb backend: {e}")
                
            # If no backend is available on Windows, automatically switch to simulation mode
            if not has_backend:
                logger.warning("No working USB backend found on Windows. Switching to simulation mode.")
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
        """Discover connected FTDI devices."""
        try:
            self.gpio_device1 = GpioMpsseController()
            self.gpio_device2 = GpioMpsseController()
            self.gpio_device3 = GpioMpsseController()
            
            # Log which backend we're using
            backend = os.environ.get('PYFTDI_BACKEND', 'default')
            logger.debug(f"FTDI device discovery using {backend} backend")
            
            # Use pyftdi's built-in device listing functionality
            from pyftdi.ftdi import Ftdi
            
            # Debug: log available backends
            logger.debug(f"Available PyFTDI backends: {', '.join(Ftdi.list_backends())}")
            
            # Set backend explicitly to help debugging
            if backend != 'default':
                logger.debug(f"Setting PyFTDI backend to: {backend}")
                Ftdi.add_custom_vendor(0x0403, 'FTDI')
                Ftdi.add_custom_product(0x0403, 0x6014, 'FT232H')
            
            # On Windows, try direct device detection as fallback
            if sys.platform == 'win32' and 'ftd2xx' in sys.modules:
                try:
                    logger.debug("Attempting direct ftd2xx device detection")
                    device_count = ftd2xx.createDeviceInfoList()
                    logger.debug(f"ftd2xx reports {device_count} devices")
                    
                    for i in range(device_count):
                        device_info = ftd2xx.getDeviceInfoDetail(i)
                        if device_info:
                            flags, device_type, device_id, description, serial = [
                                device_info[k] for k in ["Flags", "Type", "ID", "Description", "SerialNumber"]
                            ]
                            logger.debug(f"Found device: Type: {device_type}, ID: {device_id}, Description: {description}, Serial: {serial}")
                            
                            # Only add the FTDI 232H devices
                            if b"FT232H" in description or device_type == 8:  # 8 is FT232H
                                device_url = f"ftdi://ftdi:232h:{serial.decode()}/1"
                                logger.info(f"Found compatible FTDI device via ftd2xx: {device_url}")
                                self.device_urls.append(device_url)
                    
                except Exception as e:
                    logger.warning(f"ftd2xx direct detection failed: {e}")
            
            # If we found devices via direct detection, skip PyFTDI detection
            if not self.device_urls:
                logger.debug("Scanning for FTDI devices using pyftdi.Ftdi.list_devices()...")
                available_devices = Ftdi.list_devices()
                
                # Process all devices found by pyftdi
                for location, desc in available_devices:
                    vendor, product, sernum = desc
                    vendor_id = vendor >> 16
                    product_id = product >> 16
                    
                    logger.debug(f"Found device: Vendor ID: 0x{vendor_id:04x}, Product ID: 0x{product_id:04x}, Serial: {sernum}")
                    
                    # Only add the FTDI 232H devices (product ID 0x6014 - C232HM-EDHSL-0)
                    if vendor_id == 0x0403 and product_id == 0x6014:
                        # Create the standard pyftdi URL
                        device_url = f"ftdi://ftdi:232h:{sernum}/1"
                        logger.info(f"Found compatible FTDI device: {device_url}")
                        self.device_urls.append(device_url)
            
            self.device_count = len(self.device_urls)
            logger.info(f"Discovered {self.device_count} FTDI devices")
            
            if self.device_count == 0:
                logger.warning("No compatible FTDI devices found. Please check device connection and driver installation.")
                logger.warning("Device detection requires FTDI C232HM-EDHSL-0 device or compatible.")
                
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
            logger.error(f"Unexpected error discovering FTDI devices: {e}", exc_info=True)
    
    def _configure_devices(self) -> None:
        """Configure discovered FTDI devices."""
        # For Windows with libusb1, we need a special approach
        import sys
        windows_libusb_mode = sys.platform == 'win32' and os.environ.get('PYFTDI_BACKEND') == 'libusb'
        
        for device_idx, url in enumerate(self.device_urls):
            try:
                # Special handling for Windows with libusb backend
                if windows_libusb_mode:
                    logger.info(f"Using Windows-specific configuration approach for {url}")
                    
                    # For Windows with libusb, we'll try a more direct approach
                    try:
                        from pyftdi.ftdi import Ftdi
                        
                        # Extract the serial number from the URL
                        # URL format is typically: ftdi://ftdi:232h:SERIAL/1
                        parts = url.split(':')
                        if len(parts) >= 4:
                            serial = parts[3].split('/')[0]
                            logger.debug(f"Extracted serial number: {serial}")
                            
                            # Create an Ftdi instance directly
                            ftdi_device = Ftdi()
                            
                            # Try to open the device directly by serial number
                            ftdi_device.open_from_url(url)
                            logger.info(f"Successfully opened FTDI device with serial {serial}")
                            
                            # Configure for MPSSE mode (mode 0)
                            ftdi_device.set_bitmode(0xFF, Ftdi.BITMODE_MPSSE)
                            logger.info(f"Set FTDI device to MPSSE mode")
                            
                            # Store the device based on index
                            if device_idx == 0:
                                self.gpio_device1._ftdi = ftdi_device
                                logger.info("Assigned to device 1 slot")
                            elif device_idx == 1:
                                self.gpio_device2._ftdi = ftdi_device
                                logger.info("Assigned to device 2 slot")
                            elif device_idx == 2:
                                self.gpio_device3._ftdi = ftdi_device
                                logger.info("Assigned to device 3 slot")
                            
                            # Continue to next device
                            continue
                        
                    except ImportError as e:
                        logger.error(f"Failed to import necessary module for direct device access: {e}")
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
        
        # Check for Windows with libusb1 - we need special handling
        import sys
        windows_libusb_mode = sys.platform == 'win32' and os.environ.get('PYFTDI_BACKEND') == 'libusb'
        
        # Direct FTDI write for Windows with libusb backend
        if windows_libusb_mode:
            devices = [
                (1, self.gpio_device1),
                (2, self.gpio_device2),
                (3, self.gpio_device3)
            ]
            
            for device_num, gpio in devices:
                if gpio and hasattr(gpio, '_ftdi') and gpio._ftdi:
                    try:
                        # Use direct FTDI API for Windows
                        ftdi_device = gpio._ftdi
                        
                        # Prepare command buffer for MPSSE mode
                        # Set all 8 bits of the ADBUS port to the BCD value
                        command = bytes([
                            0x80,           # Command: Set data bits low byte
                            bcd_value & 0xFF,  # Value
                            0xFF            # Direction (all output)
                        ])
                        
                        # Write the command
                        ftdi_device.write_data(command)
                        logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device {device_num} using direct FTDI API")
                    except Exception as e:
                        logger.error(f"Error writing directly to FTDI device {device_num}: {e}")
                        # If direct write fails, fall back to simulation mode
                        logger.warning(f"Direct FTDI write failed, switching to simulation mode")
                        self.simulation_mode = True
                        break
            
            # If we've switched to simulation mode, return after logging
            if self.simulation_mode:
                logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
                return
            
            # If we successfully wrote via direct method, we're done
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
            
        # Check for Windows with libusb1 - we need special handling
        import sys
        windows_libusb_mode = sys.platform == 'win32' and os.environ.get('PYFTDI_BACKEND') == 'libusb'
        
        devices = [
            (1, self.gpio_device1),
            (2, self.gpio_device2),
            (3, self.gpio_device3)
        ]
        
        for device_num, gpio in devices:
            if gpio:
                try:
                    # Direct close for Windows with libusb backend
                    if windows_libusb_mode and hasattr(gpio, '_ftdi') and gpio._ftdi:
                        logger.info(f"Closing FTDI device {device_num} with direct method")
                        try:
                            gpio._ftdi.close()
                            logger.info(f"Successfully closed FTDI device {device_num} with direct method")
                        except Exception as e:
                            logger.error(f"Error closing FTDI device {device_num} with direct method: {e}")
                    else:
                        # Standard close
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