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
            # Get the raw git describe output
            raw_version = subprocess.check_output(['git', 'describe', '--tags', '--dirty'], 
                                               stderr=subprocess.DEVNULL).decode().strip()
            
            # Remove 'v' prefix if present
            if raw_version.startswith('v'):
                raw_version = raw_version[1:]
            
            # Convert to PEP 440 compatible version
            # If it's just a tag, use it directly
            if '-' not in raw_version:
                return raw_version
            
            # If it's a tag-commits-hash format, convert to tag.dev+commits.hash
            parts = raw_version.split('-')
            base_version = parts[0]
            
            # If it's dirty, handle that separately
            is_dirty = parts[-1] == 'dirty'
            if is_dirty:
                parts = parts[:-1]
            
            if len(parts) >= 3:
                commit_count = parts[1]
                commit_hash = parts[2]
                version = f"{base_version}.dev{commit_count}+{commit_hash}"
            else:
                version = base_version
                
            # Add local version identifier for dirty working directory
            if is_dirty:
                version += "+dirty"
                
            return version
    except Exception as e:
        logger.warning(f"Could not determine version from git describe: {e}")
    
    # Fallback version
    return '1.0.0'

# Package version
__version__ = get_version()