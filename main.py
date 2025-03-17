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
    important_env_vars = ["PYTHONPATH", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "PATH"]
    for var in important_env_vars:
        if var in os.environ:
            logger.info(f"Environment variable {var}: {os.environ[var]}")

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