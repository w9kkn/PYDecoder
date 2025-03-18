#!/usr/bin/env python3
"""
PYDecoder - UDP Broadcast to AntennaGenius and FTDI BCD Translator

This program serves as a translator utility to convert radio frequency data
in N1MM+ style UDP radio information broadcasts to both FTDI C232HM MPSSE
GPIO USB cables and a 4O3A Antenna Genius.
"""

import logging
import sys
import os

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='pydecoder.log',
    filemode='w'
)

# Add console handler for debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

# Get the root logger
logger = logging.getLogger()

# Configure USB backend based on platform
libusb_loaded = False
ftd2xx_loaded = False

if sys.platform == 'win32':
    # On Windows, prefer ftd2xx as it's more reliable
    try:
        import ftd2xx
        logger.info("Successfully imported ftd2xx driver, will use ftd2xx backend")
        os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
        ftd2xx_loaded = True
    except ImportError:
        logger.warning("ftd2xx driver not available on Windows, falling back to libusb")
        ftd2xx_loaded = False
    
    # Only if ftd2xx failed, try libusb
    if not ftd2xx_loaded:
        # Check if libusb-1.0.dll exists in our directory
        libusb_dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libusb-1.0.dll')
        if os.path.exists(libusb_dll_path):
            logger.info(f"Found libusb-1.0.dll at {libusb_dll_path}")
            try:
                # Try to use it directly
                import usb.backend.libusb1
                backend = usb.backend.libusb1.get_backend(find_library=lambda x: libusb_dll_path)
                if backend:
                    logger.info("Successfully initialized libusb1 backend with local DLL")
                    os.environ['PYFTDI_BACKEND'] = 'libusb'
                    libusb_loaded = True
                else:
                    logger.warning("Could not initialize libusb1 backend with local DLL")
            except Exception as e:
                logger.warning(f"Error initializing libusb backend with local DLL: {e}")
    
    # Log the selected backend
    if ftd2xx_loaded:
        logger.info("Using ftd2xx backend on Windows - this is the preferred option")
    elif libusb_loaded:
        logger.info("Using libusb backend on Windows")
    else:
        logger.warning("No USB backend successfully loaded on Windows. Device detection may fail.")
else:
    # Try to initialize libusb backend on non-Windows platforms
    try:
        import usb.backend.libusb1
        import libusb_package
        backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        if backend:
            logger.info("Successfully initialized libusb_package backend")
            libusb_loaded = True
        else:
            logger.warning("libusb backend initialization failed")
    except ImportError:
        logger.warning("libusb_package not available, using default backend")
    except Exception as e:
        logger.warning(f"Error initializing libusb backend: {e}")

from pydecoder import __version__
from pydecoder.ui.main_window import DecoderUI

# Get the root logger
logger = logging.getLogger()

def check_system_environment():
    """Check and log system environment information."""
    logger.info("System environment:")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # List environment variables that might affect FTDI USB access
    important_env_vars = ["PYTHONPATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "PATH", "PYFTDI_BACKEND"]
    for var in important_env_vars:
        if var in os.environ:
            logger.info(f"Environment variable {var}: {os.environ[var]}")
    
    # On Windows, check driver and DLL availability in detail
    if sys.platform == 'win32':
        try:
            # Check libusb-1.0.dll status
            libusb_dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libusb-1.0.dll')
            if os.path.exists(libusb_dll_path):
                logger.info(f"libusb-1.0.dll exists at {libusb_dll_path}")
                dll_size = os.path.getsize(libusb_dll_path)
                logger.info(f"libusb-1.0.dll size: {dll_size} bytes")
            else:
                logger.warning("libusb-1.0.dll not found in application directory")
            
            # Check ftd2xx status
            try:
                import ftd2xx
                logger.info(f"ftd2xx version: {ftd2xx.__version__}")
                device_count = ftd2xx.createDeviceInfoList()
                logger.info(f"ftd2xx reports {device_count} connected devices")
                for i in range(device_count):
                    device_info = ftd2xx.getDeviceInfoDetail(i)
                    if device_info:
                        logger.info(f"FTDI device {i}: {device_info}")
            except ImportError:
                logger.warning("ftd2xx module not available")
            except Exception as e:
                logger.warning(f"Error accessing ftd2xx info: {e}")
                
            # Try direct USB device enumeration
            try:
                import usb.core
                devices = list(usb.core.find(find_all=True, idVendor=0x0403))  # FTDI vendor ID
                logger.info(f"PyUSB found {len(devices)} FTDI devices")
                for i, dev in enumerate(devices):
                    logger.info(f"USB device {i}: vendor=0x{dev.idVendor:04x}, product=0x{dev.idProduct:04x}")
            except Exception as e:
                logger.warning(f"Error enumerating USB devices: {e}")
                
        except Exception as e:
            logger.warning(f"Error during Windows device check: {e}")

def main():
    """Main entry point for the application."""
    try:
        # Log startup information
        logger.info(f"Starting PYDecoder v{__version__}")
        
        # Log system environment information
        check_system_environment()
        
        # Create and run the application
        app = DecoderUI()
        app.run()
        
        return 0
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())