"""Tests for the DecoderEngine class."""

import unittest
from unittest.mock import Mock, patch, MagicMock

from pydecoder.core.decoder_engine import DecoderEngine
from pydecoder.config import LOGGER_IP_KEY, LOGGER_UDP_KEY, AG_IP_KEY, AG_TCP_PORT_KEY, AG_RF_PORT_KEY


class TestDecoderEngine(unittest.TestCase):
    """Test cases for DecoderEngine functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock objects
        self.mock_ftdi_manager = Mock()
        self.mock_antenna_genius = Mock()
        self.mock_n1mm_listener = Mock()
        
        # Create a test settings dictionary
        self.test_settings = {
            LOGGER_IP_KEY: "192.168.1.100",
            LOGGER_UDP_KEY: "12345",
            AG_IP_KEY: "192.168.1.200",
            AG_TCP_PORT_KEY: "9876",
            AG_RF_PORT_KEY: "2"
        }
        
        # Create patches
        self.ftdi_patcher = patch('pydecoder.core.decoder_engine.FTDIDeviceManager')
        self.ag_patcher = patch('pydecoder.core.decoder_engine.AntennaGenius')
        self.n1mm_patcher = patch('pydecoder.core.decoder_engine.N1MMListener')
        
        # Start patches
        self.mock_ftdi_class = self.ftdi_patcher.start()
        self.mock_ag_class = self.ag_patcher.start()
        self.mock_n1mm_class = self.n1mm_patcher.start()
        
        # Configure mocks
        self.mock_ftdi_class.return_value = self.mock_ftdi_manager
        self.mock_ag_class.return_value = self.mock_antenna_genius
        self.mock_n1mm_class.return_value = self.mock_n1mm_listener
        
        # Create a callback for testing
        self.mock_callback = Mock()
        
        # Create an engine instance for testing
        self.engine = DecoderEngine(self.test_settings, self.mock_callback)
    
    def tearDown(self):
        """Clean up test environment."""
        # Stop patches
        self.ftdi_patcher.stop()
        self.ag_patcher.stop()
        self.n1mm_patcher.stop()
    
    def test_init(self):
        """Test engine initialization."""
        # Check that components were initialized
        self.mock_ftdi_class.assert_called_once()
        self.mock_ag_class.assert_called_once_with(self.mock_callback)
        self.mock_n1mm_class.assert_called_once()
        
        # Check initial state
        self.assertEqual(self.engine.settings, self.test_settings)
        self.assertFalse(self.engine.is_active)
        self.assertEqual(self.engine.radio_freq, 0)
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        # Test starting
        self.engine.start_monitoring()
        self.assertTrue(self.engine.is_active)
        
        # Test stopping
        self.engine.stop_monitoring()
        self.assertFalse(self.engine.is_active)
    
    def test_update_frequency_inactive(self):
        """Test that update_frequency does nothing when inactive."""
        result = self.engine.update_frequency()
        self.assertIsNone(result)
        
        # Verify no component methods were called
        self.mock_n1mm_listener.setup_socket.assert_not_called()
        self.mock_n1mm_listener.receive_data.assert_not_called()
        self.mock_antenna_genius.set_antenna.assert_not_called()
        self.mock_ftdi_manager.write_bcd.assert_not_called()
    
    def test_update_frequency_no_socket(self):
        """Test update_frequency when N1MM listener needs to set up socket."""
        # Set active state
        self.engine.is_active = True
        
        # Configure mocks
        self.mock_n1mm_listener.sock = None
        self.mock_n1mm_listener.setup_socket.return_value = True
        self.mock_n1mm_listener.receive_data.return_value = None
        
        # Call update_frequency
        result = self.engine.update_frequency()
        
        # Verify result
        self.assertIsNone(result)
        
        # Verify socket setup was attempted
        self.mock_n1mm_listener.setup_socket.assert_called_once_with(
            self.test_settings[LOGGER_IP_KEY], 
            int(self.test_settings[LOGGER_UDP_KEY])
        )
        
        # Verify data reception was attempted
        self.mock_n1mm_listener.receive_data.assert_called_once()
        
        # Verify no device updates were performed
        self.mock_antenna_genius.set_antenna.assert_not_called()
        self.mock_ftdi_manager.write_bcd.assert_not_called()
    
    def test_update_frequency_with_data(self):
        """Test update_frequency with valid radio data."""
        # Set active state
        self.engine.is_active = True
        
        # Configure mocks
        self.mock_n1mm_listener.sock = MagicMock()  # Socket exists
        self.mock_n1mm_listener.receive_data.return_value = {
            "RadioInfo": {
                "RadioNr": "1",
                "Freq": "1415000"  # 14150.00 kHz
            }
        }
        
        # Call update_frequency
        result = self.engine.update_frequency()
        
        # Verify result
        self.assertEqual(result, 14150.0)
        self.assertEqual(self.engine.radio_freq, 14150.0)
        
        # Verify data reception was attempted
        self.mock_n1mm_listener.receive_data.assert_called_once()
        
        # Verify device updates were performed
        self.mock_antenna_genius.set_antenna.assert_called_once()
        self.mock_ftdi_manager.write_bcd.assert_called_once()
    
    def test_shutdown(self):
        """Test engine shutdown."""
        # Call shutdown
        self.engine.shutdown()
        
        # Verify resources were closed
        self.mock_n1mm_listener.close.assert_called_once()
        self.mock_ftdi_manager.close.assert_called_once()
    
    def test_get_current_band(self):
        """Test get_current_band method."""
        # Set a frequency
        self.engine.radio_freq = 14150
        
        # Check band name
        self.assertEqual(self.engine.get_current_band(), "20m")
    
    def test_get_current_frequency(self):
        """Test get_current_frequency method."""
        # Set a frequency
        self.engine.radio_freq = 14150
        
        # Check frequency
        self.assertEqual(self.engine.get_current_frequency(), 14150)
    
    def test_get_device_urls(self):
        """Test get_device_urls method."""
        # Configure mock
        self.mock_ftdi_manager.get_device_urls.return_value = ["ftdi://device1", "ftdi://device2"]
        
        # Call method
        result = self.engine.get_device_urls()
        
        # Verify result
        self.assertEqual(result, ["ftdi://device1", "ftdi://device2"])
        self.mock_ftdi_manager.get_device_urls.assert_called_once()


if __name__ == '__main__':
    unittest.main()