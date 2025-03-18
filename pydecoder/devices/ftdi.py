"""FTDI device handling for PYDecoder.

This module provides functionality to interact with FTDI devices, primarily
focusing on FT232H devices for BCD output. It implements two approaches:

1. Standard approach: Using pyftdi's GpioMpsseController for device access
2. Direct approach: Using ftd2xx library directly for more reliable device access

The module will automatically try the direct approach first for more reliable operation, 
and fall back to the standard approach if necessary. If hardware access fails entirely,
it will switch to simulation mode.
"""
from typing import List, Optional

import logging
import os
import sys
import pyftdi.ftdi
from pyftdi.gpio import GpioMpsseController

logger = logging.getLogger(__name__)

# Check if backend was already selected in main.py
backend = os.environ.get('PYFTDI_BACKEND', '')
if backend == 'ftd2xx':
    logger.debug("Using ftd2xx backend as configured in main.py")
else:
    # Always ensure we're using ftd2xx backend
    try:
        import ftd2xx
        logger.debug("Successfully imported ftd2xx driver")
        os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
        logger.info("Using ftd2xx backend for FTDI device access")
    except ImportError:
        logger.error("ftd2xx driver not available. It is required for this application.")
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
        # Using device indices that match ftd2xx indexing (starting at 0)
        self.gpio_device0: Optional[GpioMpsseController] = None
        self.gpio_device1: Optional[GpioMpsseController] = None 
        self.gpio_device2: Optional[GpioMpsseController] = None
        # Direct ftd2xx device handles for direct mode
        self._ft232h_device0 = None
        self._ft232h_device1 = None
        self._ft232h_device2 = None
        # Flag to indicate if we're using direct ftd2xx mode instead of pyftdi's abstraction layer
        # This is set to True when we successfully configure a device using direct ftd2xx approach
        self._direct_mode = False
        
        self.device_urls: List[str] = []
        self.device_count: int = 0
        self.simulation_mode = simulation_mode
        # Store device serials to bridge the gap between detection methods
        self.detected_serials: dict = {}
        # Track which devices are actually configured
        self.configured_devices: list = []
        
        # Check if we should use simulation mode
        # First, make sure our environment is set up for ftd2xx
        if not simulation_mode:
            # Always ensure we're using ftd2xx backend
            current_backend = os.environ.get('PYFTDI_BACKEND', '')
            if current_backend != 'ftd2xx':
                logger.info("Setting PYFTDI_BACKEND to ftd2xx")
                os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
            
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
                logger.warning("ftd2xx not available, required for hardware mode")
                
            # If ftd2xx is not available or not working, switch to simulation mode
            if not has_backend:
                logger.warning("No working ftd2xx backend found. Switching to simulation mode.")
                self.simulation_mode = True
            else:
                # Register FTDI vendor/product IDs to ensure pyftdi can use them
                try:
                    from pyftdi.ftdi import Ftdi
                    Ftdi.add_custom_vendor(0x0403, 'FTDI')
                    Ftdi.add_custom_product(0x0403, 0x6014, 'FT232H')
                    Ftdi.add_custom_product(0x0403, 0x6001, 'FT232R')
                    logger.debug("Registered FTDI vendor and product IDs with pyftdi")
                except Exception as e:
                    logger.warning(f"Failed to register FTDI IDs with pyftdi: {e}")
        
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
            self.gpio_device0 = GpioMpsseController()
            self.gpio_device1 = GpioMpsseController()
            self.gpio_device2 = GpioMpsseController()
            
            # Log which backend we're using
            backend = os.environ.get('PYFTDI_BACKEND', 'default')
            logger.debug(f"FTDI device discovery using {backend} backend")
            
            # Debug: log current backend
            logger.debug(f"Using PyFTDI backend: {backend}")
            
            # For ftd2xx backend, we don't use pyftdi's device listing
            
            # Use only ftd2xx for device detection
            try:
                logger.info("Detecting FTDI devices using only ftd2xx")
                import ftd2xx  # Import directly within this scope
                device_count = ftd2xx.createDeviceInfoList()
                logger.debug(f"ftd2xx reports {device_count} devices")
                
                device_found = False  # Track if we found any compatible devices
                for i in range(device_count):
                    logger.debug(f"Processing device {i}")
                    device_info = ftd2xx.getDeviceInfoDetail(i)
                    if device_info:
                        logger.debug(f"Raw device info for device {i}: {device_info}")
                        # Safer access to device details with fallbacks
                        # From the log output, it appears the keys are: 'index', 'flags', 'type', 'id', 'location', 'serial', 'description'
                        try:
                            # Directly match the keys from the log output
                            flags = device_info.get("flags", 0)
                            device_type = device_info.get("type", 0)
                            device_id = device_info.get("id", 0) 
                            description = device_info.get("description", b"Unknown")
                            serial = device_info.get("serial", None)
                            logger.debug(f"Accessed device details using get() method")
                        except (AttributeError, TypeError):
                            # Fall back to direct dictionary access
                            logger.debug(f"Error with get(), trying direct dictionary access")
                            try:
                                flags = device_info["flags"]
                                device_type = device_info["type"]
                                device_id = device_info["id"]
                                description = device_info["description"]
                                serial = device_info["serial"]
                            except (KeyError, TypeError) as e:
                                logger.warning(f"Could not access device info fields: {e}")
                                flags = 0
                                device_type = 0
                                device_id = 0
                                description = b"Unknown"
                                serial = None
                        logger.debug(f"Found device: Type: {device_type}, ID: {device_id}, Description: {description}, Serial: {serial}")
                        
                        # Safely access attributes that might be missing
                        serial_str = serial.decode() if serial else f"UNKNOWN{i}"
                        desc_str = description.decode() if description else f"UNKNOWN{i}"
                        logger.debug(f"Serial string: {serial_str}")
                        logger.debug(f"Description string: {desc_str}")
                        
                        # Store device info keyed by product ID for later use (0x6014 = FT232H)
                        # Check for C232HM devices in both binary and string formats (after decoding)
                        is_c232hm = False
                        if description and (b"232H" in description or b"C232HM" in description or b"C232HM-EDHSL-0" in description):
                            is_c232hm = True
                        elif desc_str and ("232H" in desc_str or "C232HM" in desc_str or "C232HM-EDHSL-0" in desc_str):
                            is_c232hm = True
                            
                        if device_type == 8 or is_c232hm:  # FT232H
                            logger.debug(f"Device {i} is FT232H type")
                            product_id = 0x6014
                            self.detected_serials[product_id] = serial_str
                            logger.debug(f"Stored serial for FT232H device: {serial_str}")
                            
                            # Only add the FTDI 232H devices
                            device_url = f"ftdi://ftdi:232h:{serial_str}/1"
                            logger.info(f"Found compatible FTDI device via ftd2xx: {device_url}")
                            self.device_urls.append(device_url)
                            device_found = True
                            logger.debug(f"Added device to device_urls, current count: {len(self.device_urls)}")
                        elif device_type == 5 or (description and b"232R" in description) or (desc_str and "232R" in desc_str):  # FT232R
                            logger.debug(f"Device {i} is FT232R type (not compatible)")
                            product_id = 0x6001
                            self.detected_serials[product_id] = serial_str
                            logger.debug(f"Stored serial for FT232R device: {serial_str}")
                    else:
                        logger.debug(f"No device info returned for device {i}")
                
                if not device_found:
                    logger.warning(f"No compatible FT232H devices found despite having {device_count} FTDI devices")
                
                logger.debug(f"Final device_urls list: {self.device_urls}")
                
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
        logger.debug(f"Configure devices - device URLs at start: {self.device_urls}")
        
        # For ftd2xx backend, we need special handling
        import sys
        ftd2xx_mode = os.environ.get('PYFTDI_BACKEND') == 'ftd2xx'
        logger.debug(f"ftd2xx mode: {ftd2xx_mode}")
        
        for device_idx, url in enumerate(self.device_urls):
            try:
                # Special handling for ftd2xx backend
                if ftd2xx_mode:
                    logger.info(f"Using ftd2xx-specific configuration approach for {url}")
                    
                    # For ftd2xx backend, we need to properly initialize GpioMpsseController
                    try:
                        # Check if we need to try an alternative approach with direct device URL
                        if "UNKNOWN" in url:
                            # If we have an UNKNOWN serial, try with first available device instead
                            logger.debug("Device has unknown serial number, trying with interface 1")
                            url = "ftdi://ftdi:232h/1"  # Use first available device
                            
                        # Properly configure the existing GpioMpsseController instance
                        if device_idx == 0 and self.gpio_device0:
                            logger.debug(f"Configuring FTDI device 0 with ftd2xx-specific approach: {url}")
                            try:
                                # Create a new controller to avoid issues with previous configuration attempts
                                self.gpio_device0 = GpioMpsseController()
                                
                                # Direct approach using ftd2xx - bypass pyftdi completely
                                # This approach uses the ftd2xx library directly to communicate with the FTDI device
                                # rather than relying on pyftdi's abstraction layer, which can have backend issues.
                                # It opens the device directly, configures it for MPSSE mode, and gives us direct access.
                                try:
                                    # Instead of using pyftdi's GPIO controller, try direct ftd2xx approach for more reliable operation
                                    import ftd2xx
                                    logger.debug("Imported ftd2xx for direct device configuration")
                                    
                                    # Extract device index from ftd2xx
                                    logger.debug(f"Trying to open FT232H device directly with ftd2xx")
                                    
                                    # Get device count
                                    device_count = ftd2xx.createDeviceInfoList()
                                    logger.debug(f"ftd2xx reports {device_count} devices for direct access")
                                    
                                    if device_count > 0:
                                        # Open the first device directly
                                        try:
                                            # Try to find the device with the matching serial number
                                            # Extract serial from URL (format is like ftdi://ftdi:232h:FT1ZT9GJ/1)
                                            serial_parts = url.split(':')
                                            if len(serial_parts) >= 4:
                                                serial = serial_parts[3].split('/')[0]
                                                logger.debug(f"Extracted serial from URL: {serial}")
                                                
                                                # Try to find device by serial
                                                found_idx = None
                                                for i in range(device_count):
                                                    dev_info = ftd2xx.getDeviceInfoDetail(i)
                                                    if dev_info and 'serial' in dev_info:
                                                        dev_serial = dev_info['serial'].decode() if dev_info['serial'] else ""
                                                        if dev_serial == serial:
                                                            found_idx = i
                                                            logger.debug(f"Found device with matching serial at index {i}")
                                                            break
                                                
                                                # If found, use that index, otherwise use 0
                                                device_idx = found_idx if found_idx is not None else 0
                                            else:
                                                device_idx = 0
                                            
                                            # Open device by index
                                            logger.debug(f"Opening device with index {device_idx}")
                                            self._ft232h_device0 = ftd2xx.open(device_idx)
                                            
                                            # Configure for MPSSE mode
                                            # Reset the device first
                                            self._ft232h_device0.resetDevice()
                                            
                                            # Set timeouts
                                            self._ft232h_device0.setTimeouts(1000, 1000)  # Set read/write timeouts
                                            
                                            # Set USB parameters
                                            self._ft232h_device0.setUSBParameters(4096, 4096)  # Set USB transfer sizes
                                            
                                            # Set flow control
                                            self._ft232h_device0.setFlowControl(0x0100, 0, 0)  # No flow control
                                            
                                            # Set bit mode to MPSSE (0x02)
                                            self._ft232h_device0.setBitMode(0, 0)  # Reset
                                            self._ft232h_device0.setBitMode(0xFF, 0x02)  # Set all pins as outputs in MPSSE mode
                                            
                                            # Initialize the MPSSE mode with proper commands
                                            # Disable clock divide by 5 for 60MHz master clock
                                            # Disable adaptive clocking
                                            # Disable three-phase clocking
                                            init_commands = bytes([
                                                0x8A, 0x97, 0x8D  # Disable special modes
                                            ])
                                            self._ft232h_device0.write(init_commands)
                                            
                                            # Initial state - set all outputs low
                                            initial_state = bytes([
                                                0x80,     # Command: set data bits low byte
                                                0x00,     # Value: all pins low
                                                0xFF      # Direction: all pins as outputs
                                            ])
                                            self._ft232h_device0.write(initial_state)
                                            
                                            # Create a simpler interface for our use
                                            self._direct_mode = True
                                            logger.info(f"Successfully configured device 0 with direct ftd2xx mode")
                                            
                                            # Track that device 0 is configured
                                            if 0 not in self.configured_devices:
                                                self.configured_devices.append(0)
                                            
                                            # Skip the pyftdi configuration
                                            return
                                        except Exception as e:
                                            logger.error(f"Error in direct ftd2xx configuration: {e}")
                                    else:
                                        logger.error("No devices reported by ftd2xx for direct access")
                                except ImportError:
                                    logger.error("Could not import ftd2xx - required for device 0 configuration")
                                
                                # Fall back to pyftdi configuration if direct approach failed
                                logger.debug("Falling back to pyftdi configuration")
                                try:
                                    # Use simpler configuration approach
                                    self.gpio_device0.configure(
                                        url, 
                                        direction=0xFF,  # All pins as outputs
                                        frequency=1e3,   # 1 kHz
                                        initial=0x0      # Initial value 0
                                    )
                                    logger.info(f"Successfully configured device 0 with pyftdi MPSSE mode")
                                    # Track that device 0 is configured
                                    if 0 not in self.configured_devices:
                                        self.configured_devices.append(0)
                                except Exception as e:
                                    logger.error(f"Error in fallback pyftdi configuration: {e}")
                            except Exception as e:
                                if "No backend available" in str(e):
                                    logger.error(f"No backend available for device 0 configuration. Make sure ftd2xx is properly installed.")
                                    logger.error(f"Current backend setting: {os.environ.get('PYFTDI_BACKEND', 'Not set')}")
                                    # Try to reinitialize the backend
                                    try:
                                        from pyftdi.backend.backend import UsbBackend
                                        # Get the available backends
                                        backends = UsbBackend.list_backends()
                                        logger.debug(f"Available backends: {backends}")
                                        if 'ftd2xx' in backends:
                                            logger.debug("ftd2xx backend is available but not being used")
                                        else:
                                            logger.error("ftd2xx backend is not available in pyftdi")
                                    except Exception as backend_error:
                                        logger.error(f"Error checking backends: {backend_error}")
                                else:
                                    logger.error(f"Error configuring device 0: {e}")
                                # Fall back to simulation for this device
                                self.gpio_device0 = None
                        elif device_idx == 1 and self.gpio_device1:
                            logger.debug(f"Configuring FTDI device 1 with ftd2xx-specific approach: {url}")
                            try:
                                # Create a new controller
                                self.gpio_device1 = GpioMpsseController()
                                
                                self.gpio_device1.configure(
                                    url, 
                                    direction=0xFF,  # All pins as outputs
                                    frequency=1e3,   # 1 kHz
                                    initial=0x0      # Initial value 0
                                )
                                logger.info(f"Successfully configured device 1 with MPSSE mode")
                                # Track that device 1 is configured
                                if 1 not in self.configured_devices:
                                    self.configured_devices.append(1)
                            except Exception as e:
                                logger.error(f"Error configuring device 1: {e}")
                                # Fall back to simulation for this device
                                self.gpio_device1 = None
                        elif device_idx == 2 and self.gpio_device2:
                            logger.debug(f"Configuring FTDI device 2 with ftd2xx-specific approach: {url}")
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
                                # Track that device 2 is configured
                                if 2 not in self.configured_devices:
                                    self.configured_devices.append(2)
                            except Exception as e:
                                logger.error(f"Error configuring device 2: {e}")
                                # Fall back to simulation for this device
                                self.gpio_device2 = None
                                
                        # Continue to next device
                        continue
                        
                    except ImportError as e:
                        logger.error(f"Failed to import necessary module for device access: {e}")
                    except Exception as e:
                        logger.error(f"Error in ftd2xx-specific device configuration: {e}")
                
                # Standard configuration approach
                if device_idx == 0 and self.gpio_device0:
                    logger.debug(f"Configuring FTDI device 0: {url}")
                    try:
                        self.gpio_device0.configure(
                            url, 
                            direction=(0xFF & ((1 << 8) - 1)), 
                            frequency=1e3, 
                            initial=0x0
                        )
                        # Track successful configuration
                        if 0 not in self.configured_devices:
                            self.configured_devices.append(0)
                        logger.info(f"Successfully configured device 0 with standard approach")
                    except Exception as e:
                        logger.error(f"Error configuring device 0 with standard approach: {e}")
                        self.gpio_device0 = None
                elif device_idx == 1 and self.gpio_device1:
                    logger.debug(f"Configuring FTDI device 1: {url}")
                    try:
                        self.gpio_device1.configure(
                            url, 
                            direction=(0xFF & ((1 << 8) - 1)), 
                            frequency=1e3, 
                            initial=0x0
                        )
                        # Track successful configuration
                        if 1 not in self.configured_devices:
                            self.configured_devices.append(1)
                        logger.info(f"Successfully configured device 1 with standard approach")
                    except Exception as e:
                        logger.error(f"Error configuring device 1 with standard approach: {e}")
                        self.gpio_device1 = None
                elif device_idx == 2 and self.gpio_device2:
                    logger.debug(f"Configuring FTDI device 2: {url}")
                    try:
                        self.gpio_device2.configure(
                            url, 
                            direction=(0xFF & ((1 << 8) - 1)), 
                            frequency=1e3, 
                            initial=0x0
                        )
                        # Track successful configuration
                        if 2 not in self.configured_devices:
                            self.configured_devices.append(2)
                        logger.info(f"Successfully configured device 2 with standard approach")
                    except Exception as e:
                        logger.error(f"Error configuring device 2 with standard approach: {e}")
                        self.gpio_device2 = None
            except pyftdi.ftdi.FtdiError as e:
                if "Operation not supported" in str(e) and os.environ.get('PYFTDI_BACKEND') == 'ftd2xx':
                    logger.warning(f"USB access limitation detected with ftd2xx backend: {e}")
                    logger.warning("This is likely due to USB driver restrictions. Try running as Administrator.")
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
                
        # Report on the final configuration state
        if self.configured_devices:
            logger.info(f"Successfully configured {len(self.configured_devices)} FTDI device(s): {self.configured_devices}")
        else:
            logger.warning("No FTDI devices were successfully configured")
            if not self.simulation_mode:
                logger.warning("Switching to simulation mode since no devices were configured")
                self.simulation_mode = True
    
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
        
        # Check for direct ftd2xx mode - this takes precedence over the pyftdi approach
        # Direct mode uses the ftd2xx library to directly write data to the FTDI device 
        # without going through pyftdi's abstraction layer, which can be more reliable
        if self._direct_mode:
            logger.debug(f"Using direct ftd2xx mode to write BCD value {bcd_value} (0x{bcd_value:02X})")
            # Write to device 0 if configured
            if 0 in self.configured_devices and self._ft232h_device0:
                try:
                    # When using MPSSE mode, we need to use proper MPSSE commands to control the GPIO pins
                    # MPSSE command 0x80 sets the lower 8 bits of the port
                    # 
                    # The command format is:
                    # 0x80: Set data bits low byte
                    # Next byte: Value to set
                    # Next byte: Direction (1 = output, 0 = input) - we've already set this in configure
                    
                    # Create MPSSE command sequence to set all GPIO pins according to BCD value
                    mpsse_command = bytes([
                        0x80,           # Command: Set data bits low byte
                        bcd_value,      # Value: the BCD value to set
                        0xFF            # Direction: all pins as outputs (already set but included for completeness)
                    ])
                    
                    # Send the MPSSE command to the device
                    bytes_written = self._ft232h_device0.write(mpsse_command)
                    if bytes_written == len(mpsse_command):
                        logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 0 using direct ftd2xx mode")
                    else:
                        logger.warning(f"Unexpected result writing to device 0: wrote {bytes_written} bytes, expected {len(mpsse_command)}")
                except Exception as e:
                    logger.error(f"Error writing to FTDI device 0 using direct ftd2xx: {e}")
                    # If write fails, remove device from configured list and check if we should switch to simulation
                    if 0 in self.configured_devices:
                        self.configured_devices.remove(0)
                    if not self.configured_devices:
                        logger.warning("All devices have encountered errors. Switching to simulation mode.")
                        self.simulation_mode = True
                        logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
            return
        
        # Standard handling using pyftdi's GpioMpsseController
        # Check for ftd2xx backend - we need special handling
        import sys
        ftd2xx_mode = os.environ.get('PYFTDI_BACKEND') == 'ftd2xx'
        
        # Use appropriate handling for ftd2xx backend
        if ftd2xx_mode:
            # Only use devices that were successfully configured
            devices = []
            if 0 in self.configured_devices and self.gpio_device0:
                devices.append((0, self.gpio_device0))
            if 1 in self.configured_devices and self.gpio_device1:
                devices.append((1, self.gpio_device1))
            if 2 in self.configured_devices and self.gpio_device2:
                devices.append((2, self.gpio_device2))
            
            # If no devices were configured, switch to simulation mode
            if not devices:
                logger.warning("No devices were successfully configured. Switching to simulation mode.")
                self.simulation_mode = True
                logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
                return
            
            for device_num, gpio in devices:
                try:
                    # Use standard GPIO write method which handles MPSSE internally
                    gpio.write(bcd_value)
                    logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device {device_num} using ftd2xx backend")
                except Exception as e:
                    logger.error(f"Error writing to FTDI device {device_num} using ftd2xx backend: {e}")
                    # If write fails, fall back to simulation mode
                    logger.warning(f"FTDI write failed with ftd2xx backend, switching to simulation mode")
                    self.simulation_mode = True
                    break
            
            # If we've switched to simulation mode, return after logging
            if self.simulation_mode:
                logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
                return
            
            # If we successfully wrote via standard method, we're done
            return
            
        # Standard GPIO write for non-ftd2xx backend
        # Only use devices that were successfully configured
        if not self.configured_devices:
            logger.warning("No devices were successfully configured. Switching to simulation mode.")
            self.simulation_mode = True
            logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
            return
            
        # Write to each configured device with individual error handling
        if 0 in self.configured_devices and self.gpio_device0:
            try:
                self.gpio_device0.write(bcd_value)
                logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 0")
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 0: {e}")
                # If we see "Operation not supported" with ftd2xx backend, switch to simulation
                if "Operation not supported" in str(e) and os.environ.get('PYFTDI_BACKEND') == 'ftd2xx':
                    logger.warning("USB access limitation detected with ftd2xx backend. Switching to simulation mode.")
                    self.simulation_mode = True
                    # Log the simulated write
                    logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
                    return
            except OSError as e:
                logger.error(f"OS error writing to device 0: {e}")
                # Remove from configured devices
                self.configured_devices.remove(0)
            except Exception as e:
                logger.error(f"Unexpected error writing to device 0: {e}")
                # Remove from configured devices
                if 0 in self.configured_devices:
                    self.configured_devices.remove(0)
                
        if 1 in self.configured_devices and self.gpio_device1:
            try:
                self.gpio_device1.write(bcd_value)
                logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 1")
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 1: {e}")
                # Remove from configured devices
                if 1 in self.configured_devices:
                    self.configured_devices.remove(1)
            except OSError as e:
                logger.error(f"OS error writing to device 1: {e}")
                # Remove from configured devices
                if 1 in self.configured_devices:
                    self.configured_devices.remove(1)
            except Exception as e:
                logger.error(f"Unexpected error writing to device 1: {e}")
                # Remove from configured devices
                if 1 in self.configured_devices:
                    self.configured_devices.remove(1)
                
        if 2 in self.configured_devices and self.gpio_device2:
            try:
                self.gpio_device2.write(bcd_value)
                logger.debug(f"Successfully wrote BCD value {bcd_value} (0x{bcd_value:02X}) to device 2")
            except pyftdi.ftdi.FtdiError as e:
                logger.error(f"FTDI driver error writing to device 2: {e}")
                # Remove from configured devices
                if 2 in self.configured_devices:
                    self.configured_devices.remove(2)
            except OSError as e:
                logger.error(f"OS error writing to device 2: {e}")
                # Remove from configured devices
                if 2 in self.configured_devices:
                    self.configured_devices.remove(2)
            except Exception as e:
                logger.error(f"Unexpected error writing to device 2: {e}")
                # Remove from configured devices
                if 2 in self.configured_devices:
                    self.configured_devices.remove(2)
                    
        # If no devices remain configured, switch to simulation mode
        if not self.configured_devices:
            logger.warning("All devices have encountered errors. Switching to simulation mode.")
            self.simulation_mode = True
            logger.info(f"SIMULATION: Writing BCD value {bcd_value} (0x{bcd_value:02X}) to FTDI devices")
    
    def close(self) -> None:
        """Close all FTDI devices and release resources.
        
        This method should be called when the application is shutting down
        to ensure proper cleanup of FTDI resources.
        """
        # In simulation mode, just log and return
        if self.simulation_mode:
            logger.info("SIMULATION: Closing simulated FTDI devices")
            return
            
        # Check for direct ftd2xx mode first
        if self._direct_mode:
            logger.info("Closing devices in direct ftd2xx mode")
            
            # Close any direct ftd2xx devices
            if self._ft232h_device0:
                try:
                    logger.info("Closing direct ftd2xx device 0")
                    self._ft232h_device0.close()
                    self._ft232h_device0 = None
                except Exception as e:
                    logger.error(f"Error closing direct ftd2xx device 0: {e}")
                
            if self._ft232h_device1:
                try:
                    logger.info("Closing direct ftd2xx device 1")
                    self._ft232h_device1.close()
                    self._ft232h_device1 = None
                except Exception as e:
                    logger.error(f"Error closing direct ftd2xx device 1: {e}")
                
            if self._ft232h_device2:
                try:
                    logger.info("Closing direct ftd2xx device 2")
                    self._ft232h_device2.close()
                    self._ft232h_device2 = None
                except Exception as e:
                    logger.error(f"Error closing direct ftd2xx device 2: {e}")
            
            # We're done with the direct devices
            return
        
        # Standard pyftdi device handling
        # Check for ftd2xx backend - we need special handling
        import sys
        ftd2xx_mode = os.environ.get('PYFTDI_BACKEND') == 'ftd2xx'
        
        # Only try to close devices that were configured
        devices = []
        if 0 in self.configured_devices and self.gpio_device0:
            devices.append((0, self.gpio_device0))
        if 1 in self.configured_devices and self.gpio_device1:
            devices.append((1, self.gpio_device1))
        if 2 in self.configured_devices and self.gpio_device2:
            devices.append((2, self.gpio_device2))
        
        # Also include any initialized but not configured devices
        if self.gpio_device0 and 0 not in self.configured_devices:
            devices.append((0, self.gpio_device0))
        if self.gpio_device1 and 1 not in self.configured_devices:
            devices.append((1, self.gpio_device1))
        if self.gpio_device2 and 2 not in self.configured_devices:
            devices.append((2, self.gpio_device2))
        
        for device_num, gpio in devices:
            if gpio:
                try:
                    # Use standard close for ftd2xx backend
                    # GpioMpsseController.close() will handle closing the underlying FTDI device
                    logger.info(f"Closing FTDI device {device_num}")
                    gpio.close()
                except pyftdi.ftdi.FtdiError as e:
                    if "Operation not supported" in str(e) and os.environ.get('PYFTDI_BACKEND') == 'ftd2xx':
                        logger.warning(f"USB access limitation detected with ftd2xx backend while closing device {device_num}: {e}")
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