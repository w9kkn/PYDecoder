"""Configuration handling for PYDecoder."""
import json
import os
from typing import Dict, Any

DEFAULT_CONFIG = {
    "logger_ip": "127.0.0.1",
    "logger_udp": "12060",
    "AG_1_IP": "192.168.100.140",
    "AG_1_UDP_Port": "9007",
    "AG_1_RF_Port": "1"
}

def load_settings() -> Dict[str, Any]:
    """Load settings from config file or return defaults if file doesn't exist."""
    try:
        with open("config.json") as json_data_file:
            return json.load(json_data_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()

def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to config file."""
    with open("config.json", "w") as json_config_file:
        json.dump(settings, json_config_file)