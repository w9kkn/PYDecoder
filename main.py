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

# Add console handler for important messages
console_handler = logging.StreamHandler()
# Using INFO level to show basic status updates but not excessive debug information
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
    # On Windows, only use ftd2xx backend
    try:
        import ftd2xx
        logger.info("Successfully imported ftd2xx driver, will use ftd2xx backend")
        os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
        ftd2xx_loaded = True
        logger.info("Using ftd2xx backend on Windows - this is the only option we're using")
    except ImportError:
        logger.error("ftd2xx driver not available on Windows. It is required for this application.")
        logger.error("Please install ftd2xx package with: pip install ftd2xx")
        ftd2xx_loaded = False
else:
    # For non-Windows platforms, we'll still use ftd2xx if available
    try:
        import ftd2xx
        logger.info("Successfully imported ftd2xx driver on non-Windows platform")
        os.environ['PYFTDI_BACKEND'] = 'ftd2xx'
        ftd2xx_loaded = True
    except ImportError:
        logger.warning("ftd2xx driver not available on non-Windows platform")
        ftd2xx_loaded = False

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
    
    # On Windows, check driver availability in detail
    if sys.platform == 'win32':
        try:
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
                
            logger.debug("Using ftd2xx exclusively for device access")
                
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