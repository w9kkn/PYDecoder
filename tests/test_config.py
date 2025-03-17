"""Tests for the config module."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from pydecoder.config import (
    load_settings, save_settings, DEFAULT_CONFIG, 
    get_config_file_path, CONFIG_FILENAME, validate_config,
    LOGGER_IP_KEY, LOGGER_UDP_KEY, AG_IP_KEY, AG_TCP_PORT_KEY, AG_RF_PORT_KEY
)


class TestConfig(unittest.TestCase):
    """Test cases for config module functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for our test files
        self.test_dir = tempfile.mkdtemp()
        self.orig_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a patch for get_config_file_path to use our test directory
        self.path_patcher = patch('pydecoder.config.get_config_file_path')
        self.mock_get_path = self.path_patcher.start()
        self.mock_get_path.return_value = Path(self.test_dir) / CONFIG_FILENAME
    
    def tearDown(self):
        """Clean up test environment."""
        self.path_patcher.stop()
        os.chdir(self.orig_dir)
        shutil.rmtree(self.test_dir)
    
    def test_get_config_file_path(self):
        """Test the config file path resolution."""
        # Stop the patch so we can test the real function
        self.path_patcher.stop()
        
        # Create a config file in the test directory
        config_path = Path(self.test_dir) / CONFIG_FILENAME
        with open(config_path, "w") as f:
            f.write("{}")
        
        # Test that the function finds our config file
        result = get_config_file_path()
        self.assertEqual(result, config_path)
        
        # Restart the patch for other tests
        self.mock_get_path = self.path_patcher.start()
        self.mock_get_path.return_value = Path(self.test_dir) / CONFIG_FILENAME
    
    def test_load_settings_default(self):
        """Test that default settings are returned when no config file exists."""
        # No config file exists yet, should return defaults
        settings = load_settings()
        self.assertEqual(settings, DEFAULT_CONFIG)
    
    def test_load_settings_from_file(self):
        """Test loading settings from an existing config file."""
        # Create a test config file
        test_config = {
            LOGGER_IP_KEY: "192.168.1.100",
            LOGGER_UDP_KEY: "12345",
            AG_IP_KEY: "192.168.1.200",
            AG_TCP_PORT_KEY: "9876",
            AG_RF_PORT_KEY: "2"
        }
        with open(self.mock_get_path.return_value, "w") as f:
            json.dump(test_config, f)
        
        # Load settings should read from the file
        settings = load_settings()
        self.assertEqual(settings, test_config)
    
    def test_load_settings_invalid_json(self):
        """Test that default settings are returned when config file contains invalid JSON."""
        # Create an invalid config file
        with open(self.mock_get_path.return_value, "w") as f:
            f.write("This is not valid JSON")
        
        # Load settings should return defaults
        settings = load_settings()
        self.assertEqual(settings, DEFAULT_CONFIG)
    
    def test_save_settings(self):
        """Test saving settings to a file."""
        test_config = {
            LOGGER_IP_KEY: "192.168.1.100",
            LOGGER_UDP_KEY: "12345",
            AG_IP_KEY: "192.168.1.200",
            AG_TCP_PORT_KEY: "9876",
            AG_RF_PORT_KEY: "2"
        }
        
        # Save the settings
        save_settings(test_config)
        
        # Verify the file was created with the correct content
        with open(self.mock_get_path.return_value, "r") as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config, test_config)
    
    def test_save_settings_permission_error(self):
        """Test error handling when saving settings fails due to permissions."""
        test_config = {
            LOGGER_IP_KEY: "192.168.1.100",
            LOGGER_UDP_KEY: "12345"
        }
        
        # Configure the mock to raise a permission error
        self.mock_get_path.return_value = Path("/root/not-writable-file.json")
        
        # This should not raise an exception even though saving will fail
        save_settings(test_config)
        
        # No need to verify anything - we're just making sure no exception is raised
        
    def test_validate_config_complete(self):
        """Test validation of a complete config."""
        test_config = {
            LOGGER_IP_KEY: "192.168.1.100",
            LOGGER_UDP_KEY: "12345",
            AG_IP_KEY: "192.168.1.200",
            AG_TCP_PORT_KEY: "9876",
            AG_RF_PORT_KEY: "2"
        }
        
        # Validate the config
        validated = validate_config(test_config)
        
        # Config should be unchanged
        self.assertEqual(validated, test_config)
        
    def test_validate_config_missing_keys(self):
        """Test validation of a config with missing keys."""
        test_config = {
            LOGGER_IP_KEY: "192.168.1.100",
            # Missing LOGGER_UDP_KEY
            AG_IP_KEY: "192.168.1.200",
            # Missing AG_TCP_PORT_KEY
            # Missing AG_RF_PORT_KEY
        }
        
        # Validate the config
        validated = validate_config(test_config)
        
        # Config should have default values for missing keys
        self.assertEqual(validated[LOGGER_IP_KEY], "192.168.1.100")
        self.assertEqual(validated[LOGGER_UDP_KEY], "12060")  # Default
        self.assertEqual(validated[AG_IP_KEY], "192.168.1.200")
        self.assertEqual(validated[AG_TCP_PORT_KEY], "9007")  # Default
        self.assertEqual(validated[AG_RF_PORT_KEY], "1")  # Default
        
    def test_validate_config_wrong_types(self):
        """Test validation of a config with wrong types."""
        test_config = {
            LOGGER_IP_KEY: 192,  # Should be a string
            LOGGER_UDP_KEY: 12345,  # Should be a string
            AG_IP_KEY: "192.168.1.200",
            AG_TCP_PORT_KEY: "9876",
            AG_RF_PORT_KEY: 2  # Should be a string
        }
        
        # Validate the config
        validated = validate_config(test_config)
        
        # Config should have correct types for all keys
        self.assertEqual(validated[LOGGER_IP_KEY], "127.0.0.1")  # Default
        self.assertEqual(validated[LOGGER_UDP_KEY], "12060")  # Default
        self.assertEqual(validated[AG_IP_KEY], "192.168.1.200")
        self.assertEqual(validated[AG_TCP_PORT_KEY], "9876")
        self.assertEqual(validated[AG_RF_PORT_KEY], "1")  # Default
        
    def test_validate_config_unknown_keys(self):
        """Test validation of a config with unknown keys."""
        test_config = {
            LOGGER_IP_KEY: "192.168.1.100",
            LOGGER_UDP_KEY: "12345",
            AG_IP_KEY: "192.168.1.200",
            AG_TCP_PORT_KEY: "9876",
            AG_RF_PORT_KEY: "2",
            "unknown_key": "value"
        }
        
        # Validate the config
        validated = validate_config(test_config)
        
        # Unknown keys should be preserved
        self.assertEqual(validated["unknown_key"], "value")


if __name__ == '__main__':
    unittest.main()