#!/usr/bin/env python3
"""
PYDecoder - UDP Broadcast to AntennaGenius and FTDI BCD Translator

This program serves as a translator utility to convert radio frequency data
in N1MM+ style UDP radio information broadcasts to both FTDI C232HM MPSSE
GPIO USB cables and a 4O3A Antenna Genius.
"""

import logging
import sys
from pydecoder import __version__
from pydecoder.ui.main_window import DecoderUI

# Get the root logger
logger = logging.getLogger()

def main():
    """Main entry point for the application."""
    try:
        # Log startup information
        logger.info(f"Starting PYDecoder v{__version__}")
        
        # Create and run the application
        app = DecoderUI()
        app.run()
        
        return 0
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())