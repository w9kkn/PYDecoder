"""Tests for AntennaGenius class."""

import socket
import unittest
from unittest.mock import Mock, patch, MagicMock, call

from pydecoder.networking.antenna_genius import AntennaGenius


class TestAntennaGenius(unittest.TestCase):
    """Test cases for AntennaGenius functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.callback = Mock()
        self.ag = AntennaGenius(self.callback)
    
    def test_init(self):
        """Test initialization."""
        # With callback
        ag = AntennaGenius(self.callback)
        self.assertEqual(ag.status_callback, self.callback)
        
        # Without callback
        ag = AntennaGenius()
        self.assertIsNone(ag.status_callback)
    
    @patch('socket.socket')
    def test_set_antenna_success(self, mock_socket_class):
        """Test successful antenna setting."""
        # Configure mock
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        
        # Call method
        result = self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify socket operations
        mock_socket.settimeout.assert_called_once_with(0.5)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 9007))
        mock_socket.sendall.assert_called_once_with(b"C0|port set 1 band=5\n")
        
        # Verify callback was called
        self.callback.assert_called_once_with("AG Message Delivered!")
    
    @patch('socket.socket')
    def test_set_antenna_address_error(self, mock_socket_class):
        """Test handling of address error."""
        # Configure mock to raise error
        mock_socket_class.return_value.__enter__.return_value = Mock()
        mock_socket_class.return_value.__enter__.side_effect = socket.gaierror("Test error")
        
        # Call method
        result = self.ag.set_antenna("invalid-address", 9007, "1", 5)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify callback was called with error message
        self.callback.assert_called_once_with("AG Comm Failure! Address error")
    
    @patch('socket.socket')
    def test_set_antenna_timeout(self, mock_socket_class):
        """Test handling of timeout error."""
        # Configure mock to raise timeout
        mock_socket_class.return_value.__enter__.return_value = Mock()
        mock_socket_class.return_value.__enter__.side_effect = socket.timeout("Test timeout")
        
        # Call method
        result = self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify callback was called with error message
        self.callback.assert_called_once_with("AG Comm Failure! Connection timeout")
    
    @patch('socket.socket')
    def test_set_antenna_connection_refused(self, mock_socket_class):
        """Test handling of connection refused error."""
        # Configure mock to raise connection refused
        mock_socket_class.return_value.__enter__.return_value = Mock()
        mock_socket_class.return_value.__enter__.side_effect = ConnectionRefusedError("Test refused")
        
        # Call method
        result = self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify callback was called with error message
        self.callback.assert_called_once_with("AG Comm Failure! Connection refused")
    
    @patch('socket.socket')
    def test_set_antenna_no_callback(self, mock_socket_class):
        """Test antenna setting with no callback provided."""
        # Create AntennaGenius instance without callback
        ag = AntennaGenius()
        
        # Configure mock
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        
        # Call method
        result = ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify socket operations
        mock_socket.settimeout.assert_called_once_with(0.5)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 9007))
        mock_socket.sendall.assert_called_once_with(b"C0|port set 1 band=5\n")


if __name__ == '__main__':
    unittest.main()