"""Configuration handling for PYDecoder."""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "logger_ip": "127.0.0.1",
    "logger_udp": "12060",
    "AG_1_IP": "192.168.100.140",
    "AG_1_UDP_Port": "9007",
    "AG_1_RF_Port": "1"
}

# Configuration keys - these are used throughout the application
# Future improvement: Normalize these keys to snake_case too
# (would require changes in UI code and migration of existing config files)
LOGGER_IP_KEY = "logger_ip"  
LOGGER_UDP_KEY = "logger_udp" 
AG_IP_KEY = "AG_1_IP"
AG_TCP_PORT_KEY = "AG_1_UDP_Port"  
AG_RF_PORT_KEY = "AG_1_RF_Port"
SIM_MODE_KEY = "enable_simulation_mode"

# Configuration validation schema
CONFIG_SCHEMA = {
    LOGGER_IP_KEY: {"type": str, "default": "127.0.0.1", "required": True},
    LOGGER_UDP_KEY: {"type": str, "default": "12060", "required": True},
    AG_IP_KEY: {"type": str, "default": "192.168.100.140", "required": True},
    AG_TCP_PORT_KEY: {"type": str, "default": "9007", "required": True},
    AG_RF_PORT_KEY: {"type": str, "default": "1", "required": True},
    SIM_MODE_KEY: {"type": bool, "default": False, "required": False}
}

# Configuration file locations
CONFIG_FILENAME = "config.json"

def get_config_file_path() -> Path:
    """Get the absolute path to the configuration file.
    
    Looks for the config file in the following locations (in order):
    1. Current working directory
    2. Directory containing the executable (for PyInstaller)
    3. Directory containing this module
    
    Returns:
        Path: The absolute path to the configuration file
    """
    # Check for config file in the current working directory
    cwd_path = Path(os.getcwd()) / CONFIG_FILENAME
    if cwd_path.exists():
        return cwd_path
    
    # Check for config file in the directory containing the executable
    # This is useful for PyInstaller bundles
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        exe_path = exe_dir / CONFIG_FILENAME
        if exe_path.exists():
            return exe_path
    
    # Check for config file in the directory containing this module
    module_dir = Path(__file__).parent.parent
    module_path = module_dir / CONFIG_FILENAME
    if module_path.exists():
        return module_path
    
    # Default to current working directory if file doesn't exist anywhere
    return cwd_path

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize configuration.
    
    Checks the configuration against the schema, ensuring:
    - All required keys are present
    - Values have the correct types
    - Missing optional values are set to defaults
    
    Args:
        config: The configuration dictionary to validate
        
    Returns:
        Dict[str, Any]: The validated and normalized configuration
    """
    validated_config = {}
    
    # Check each key in the schema
    for key, schema in CONFIG_SCHEMA.items():
        # Check if key exists in config
        if key in config:
            value = config[key]
            
            # Check value type
            if not isinstance(value, schema["type"]):
                logger.warning(f"Config key '{key}' has wrong type {type(value).__name__}, "
                              f"expected {schema['type'].__name__}. Using default.")
                validated_config[key] = schema["default"]
            else:
                validated_config[key] = value
        elif schema.get("required", False):
            # Key is required but missing, use default
            logger.warning(f"Required config key '{key}' is missing. Using default.")
            validated_config[key] = schema["default"]
    
    # Check for unknown keys in config
    for key in config.keys():
        if key not in CONFIG_SCHEMA:
            logger.warning(f"Unknown config key '{key}'")
            # Keep unknown keys in the config
            validated_config[key] = config[key]
    
    return validated_config


def load_settings() -> Dict[str, Any]:
    """Load settings from config file or return defaults if file doesn't exist.
    
    Attempts to read the configuration from config.json using the search path defined
    in get_config_file_path(). If the file doesn't exist or contains invalid JSON,
    returns the default configuration.
    
    The loaded configuration is validated against the schema to ensure it contains
    all required keys with the correct types.
    
    Returns:
        Dict[str, Any]: A dictionary containing validated application settings
    """
    config_path = get_config_file_path()
    
    try:
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return DEFAULT_CONFIG.copy()
            
        with open(config_path) as json_data_file:
            config = json.load(json_data_file)
            logger.info(f"Configuration loaded from {config_path}")
            
            # Validate the loaded configuration
            validated_config = validate_config(config)
            
            # If validation modified the config, save the changes
            if validated_config != config:
                logger.info("Configuration was modified during validation, saving changes")
                save_settings(validated_config)
                
            return validated_config
            
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file at {config_path}, using defaults")
        return DEFAULT_CONFIG.copy()
    except (PermissionError, OSError) as e:
        logger.error(f"Error accessing config file at {config_path}: {e}")
        return DEFAULT_CONFIG.copy()

def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to config file.
    
    Writes the settings dictionary to config.json. The location is determined
    by the following logic:
    1. If a config file already exists at a location found by get_config_file_path(),
       that file will be updated.
    2. If no config file exists, it will be created in the current working directory.
    
    The settings are validated before saving to ensure they conform to the schema.
    
    Args:
        settings: Dictionary containing application settings to save
    """
    # Validate settings before saving
    validated_settings = validate_config(settings)
    try:
        # Determine where to save the config file
        config_path = get_config_file_path()
        
        # Create parent directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the settings to the file
        with open(config_path, "w") as json_config_file:
            json.dump(validated_settings, json_config_file, indent=4)  # Pretty formatting
            logger.info(f"Configuration saved to {config_path}")
    except (PermissionError, OSError) as e:
        logger.error(f"Error saving configuration to {config_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving configuration: {e}")