"""PYDecoder package for N1MM+ UDP to FTDI BCD and 4O3A Antenna Genius translation."""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger for the package
logger = logging.getLogger('pydecoder')

# Package version
__version__ = '1.0.0'