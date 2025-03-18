"""Tests for FTDIDeviceManager class."""

import unittest
from unittest.mock import Mock, patch, MagicMock, call

import pyftdi
from pyftdi.gpio import GpioMpsseController

from pydecoder.devices.ftdi import FTDIDeviceManager


class TestFTDIDeviceManager(unittest.TestCase):
    """Test cases for FTDIDeviceManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create patches
        self.gpio_controller_patcher = patch('pydecoder.devices.ftdi.GpioMpsseController')
        self.ftdi_list_devices_patcher = patch('pyftdi.ftdi.Ftdi.list_devices')
        self.ftd2xx_patcher = patch('pydecoder.devices.ftdi.ftd2xx')
        self.env_patcher = patch.dict('os.environ', {'PYFTDI_BACKEND': 'ftd2xx'})
        
        # Start patches
        self.mock_gpio_controller = self.gpio_controller_patcher.start()
        self.mock_list_devices = self.ftdi_list_devices_patcher.start()
        self.mock_ftd2xx = self.ftd2xx_patcher.start()
        self.env_patcher.start()
        
        # Configure ftd2xx mock
        self.mock_ftd2xx.createDeviceInfoList.return_value = 3
        self.mock_ftd2xx.getDeviceInfoDetail.side_effect = [
            {'index': 0, 'flags': 2, 'type': 8, 'id': 67330068, 'location': 40, 'serial': b'A123', 'description': b'C232HM-EDHSL-0'},
            {'index': 1, 'flags': 2, 'type': 8, 'id': 67330068, 'location': 41, 'serial': b'B456', 'description': b'C232HM-EDHSL-0'},
            {'index': 2, 'flags': 2, 'type': 8, 'id': 67330068, 'location': 42, 'serial': b'C789', 'description': b'C232HM-EDHSL-0'},
        ]
        
        # For direct ftd2xx mode, mock the open and device methods
        self.mock_ft_device = Mock()
        self.mock_ftd2xx.open.return_value = self.mock_ft_device
        
        # Configure list_devices mock to return some test devices
        self.mock_list_devices.return_value = [
            ((0, 0, 0, 0, "A123", 0, "C232HM-EDHSL-0"), {}),
            ((0, 0, 0, 0, "B456", 0, "C232HM-EDHSL-0"), {}),
            ((0, 0, 0, 0, "C789", 0, "C232HM-EDHSL-0"), {})
        ]
        
        # Configure GPIO controller mock
        self.mock_gpio1 = Mock()
        self.mock_gpio2 = Mock()
        self.mock_gpio3 = Mock()
        self.mock_gpio_controller.side_effect = [self.mock_gpio1, self.mock_gpio2, self.mock_gpio3]
    
    def tearDown(self):
        """Clean up test environment."""
        # Stop patches
        self.gpio_controller_patcher.stop()
        self.ftdi_list_devices_patcher.stop()
        self.ftd2xx_patcher.stop()
        self.env_patcher.stop()
    
    def test_init(self):
        """Test device manager initialization and discovery."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Verify GPIO controllers were created
        self.assertEqual(self.mock_gpio_controller.call_count, 3)
        
        # Verify device discovery
        self.mock_list_devices.assert_called_once()
        
        # Verify devices were discovered correctly
        expected_urls = [
            "ftdi://ftdi:232h:A123/1",
            "ftdi://ftdi:232h:B456/1",
            "ftdi://ftdi:232h:C789/1"
        ]
        self.assertEqual(manager.device_urls, expected_urls)
        self.assertEqual(manager.device_count, 3)
        
        # Verify device configuration
        self.mock_gpio1.configure.assert_called_once()
        self.mock_gpio2.configure.assert_called_once()
        self.mock_gpio3.configure.assert_called_once()
    
    def test_discover_devices_with_exception(self):
        """Test error handling in device discovery."""
        # Configure list_devices to raise an exception
        self.mock_list_devices.side_effect = pyftdi.ftdi.FtdiError("Test error")
        
        # Create manager instance (should not raise exception)
        manager = FTDIDeviceManager()
        
        # Verify no devices were discovered
        self.assertEqual(manager.device_urls, [])
        self.assertEqual(manager.device_count, 0)
    
    def test_write_bcd(self):
        """Test writing BCD values to devices."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Write a BCD value
        manager.write_bcd(0b0101)  # 5
        
        # Verify write to all devices
        self.mock_gpio1.write.assert_called_once_with(0b0101)
        self.mock_gpio2.write.assert_called_once_with(0b0101)
        self.mock_gpio3.write.assert_called_once_with(0b0101)
    
    def test_write_bcd_out_of_range(self):
        """Test writing out-of-range BCD values."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Write an out-of-range BCD value
        manager.write_bcd(1000)  # > 255
        
        # Verify value was clamped to 255
        self.mock_gpio1.write.assert_called_once_with(255)
        self.mock_gpio2.write.assert_called_once_with(255)
        self.mock_gpio3.write.assert_called_once_with(255)
    
    def test_write_bcd_with_exception(self):
        """Test error handling in BCD writing."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Configure first device to raise an exception
        self.mock_gpio1.write.side_effect = pyftdi.ftdi.FtdiError("Test error")
        
        # Write a BCD value (should not propagate exception)
        manager.write_bcd(0b0101)
        
        # Verify write was attempted on all devices
        self.mock_gpio1.write.assert_called_once_with(0b0101)
        self.mock_gpio2.write.assert_called_once_with(0b0101)
        self.mock_gpio3.write.assert_called_once_with(0b0101)
        
        # Verify device 0 was removed from configured devices after the error
        self.assertNotIn(0, manager.configured_devices)
        
    def test_direct_ftd2xx_mode(self):
        """Test direct ftd2xx mode."""
        # Force the direct mode initialization by making the regular mode fail
        # Configure the GPIO mock to raise an exception during configure
        self.mock_gpio1.configure.side_effect = pyftdi.ftdi.FtdiError("No backend available")
        
        # Create manager instance - should use direct ftd2xx mode
        manager = FTDIDeviceManager()
        
        # Verify direct mode was enabled
        self.assertTrue(manager._direct_mode)
        
        # Verify ftd2xx open was called
        self.mock_ftd2xx.open.assert_called()
        
        # Verify device was properly configured
        self.mock_ft_device.setBitMode.assert_any_call(0xFF, 0x02)
        self.mock_ft_device.setTimeouts.assert_called_with(1000, 1000)
        self.mock_ft_device.resetDevice.assert_called_once()
        
        # Verify initialization commands were sent
        expected_calls = [
            mock.call(bytes([0x8A, 0x97, 0x8D])),  # Init commands
            mock.call(bytes([0x80, 0x00, 0xFF]))   # Initial state
        ]
        self.mock_ft_device.write.assert_has_calls(expected_calls, any_order=False)
        
        # Reset write mock to check BCD write specifically
        self.mock_ft_device.write.reset_mock()
        
        # Write a BCD value in direct mode
        manager.write_bcd(0b0101)
        
        # Verify proper MPSSE command sequence was used
        expected_mpsse_cmd = bytes([
            0x80,      # Command to set data bits low
            0b0101,    # BCD value
            0xFF       # Direction (all outputs)
        ])
        self.mock_ft_device.write.assert_called_with(expected_mpsse_cmd)
        
        # Verify device 0 is in the configured devices list
        self.assertIn(0, manager.configured_devices)
    
    def test_close(self):
        """Test closing devices."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Close devices
        manager.close()
        
        # Verify close was called on all devices
        self.mock_gpio1.close.assert_called_once()
        self.mock_gpio2.close.assert_called_once()
        self.mock_gpio3.close.assert_called_once()
    
    def test_close_with_exception(self):
        """Test error handling when closing devices."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Configure first device to raise an exception
        self.mock_gpio1.close.side_effect = pyftdi.ftdi.FtdiError("Test error")
        
        # Close devices (should not propagate exception)
        manager.close()
        
        # Verify close was attempted on all devices
        self.mock_gpio1.close.assert_called_once()
        self.mock_gpio2.close.assert_called_once()
        self.mock_gpio3.close.assert_called_once()
        
    def test_close_direct_mode(self):
        """Test closing in direct ftd2xx mode."""
        # Force the direct mode initialization by making the regular mode fail
        self.mock_gpio1.configure.side_effect = pyftdi.ftdi.FtdiError("No backend available")
        
        # Create manager instance - should use direct ftd2xx mode
        manager = FTDIDeviceManager()
        
        # Verify direct mode was enabled
        self.assertTrue(manager._direct_mode)
        
        # Close devices
        manager.close()
        
        # Verify ftd2xx device was closed
        self.mock_ft_device.close.assert_called_once()
        
        # Verify GPIO close wasn't called (since we're in direct mode)
        self.mock_gpio1.close.assert_not_called()
        self.mock_gpio2.close.assert_not_called()
        self.mock_gpio3.close.assert_not_called()
    
    def test_get_device_urls(self):
        """Test getting device URLs."""
        # Create manager instance
        manager = FTDIDeviceManager()
        
        # Get device URLs
        urls = manager.get_device_urls()
        
        # Verify correct URLs were returned
        expected_urls = [
            "ftdi://ftdi:232h:A123/1",
            "ftdi://ftdi:232h:B456/1",
            "ftdi://ftdi:232h:C789/1"
        ]
        self.assertEqual(urls, expected_urls)


if __name__ == '__main__':
    unittest.main()