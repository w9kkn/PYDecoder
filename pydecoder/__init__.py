"""PYDecoder package for N1MM+ UDP to FTDI BCD and 4O3A Antenna Genius translation."""

import logging
import subprocess
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger for the package
logger = logging.getLogger('pydecoder')

# Get version from git describe or fallback to default
def get_version():
    try:
        # Get version with git describe if in a git repository
        if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.git')):
            version = subprocess.check_output(['git', 'describe', '--tags', '--dirty'], 
                                             stderr=subprocess.DEVNULL).decode().strip()
            # Remove 'v' prefix if present
            if version.startswith('v'):
                version = version[1:]
            return version
    except Exception as e:
        logger.warning(f"Could not determine version from git describe: {e}")
    
    # Fallback version
    return '1.0.0'

# Package version
__version__ = get_version()