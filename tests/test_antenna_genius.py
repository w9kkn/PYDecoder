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
        self.assertIsNone(ag.socket)
        self.assertEqual(ag.command_counter, 0)
        
        # Without callback
        ag = AntennaGenius()
        self.assertIsNone(ag.status_callback)
        self.assertIsNone(ag.socket)
        self.assertEqual(ag.command_counter, 0)
    
    @patch('socket.socket')
    def test_set_antenna_success(self, mock_socket_class):
        """Test successful antenna setting."""
        # Configure mock
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # Call method
        result = self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify socket operations
        mock_socket.settimeout.assert_called_once_with(0.5)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 9007))
        mock_socket.sendall.assert_called_once_with(b"C1|port set 1 band=5 \n")
        
        # Verify callback was called
        self.callback.assert_called_once_with("AG Message Delivered!")
        
        # Verify command counter incremented
        self.assertEqual(self.ag.command_counter, 1)
    
    @patch('socket.socket')
    def test_set_antenna_address_error(self, mock_socket_class):
        """Test handling of address error."""
        # Configure mock to raise error
        mock_socket_class.return_value.connect.side_effect = socket.gaierror("Test error")
        
        # Call method
        result = self.ag.set_antenna("invalid-address", 9007, "1", 5)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify callback was called with error message
        self.callback.assert_called_once_with("AG Comm Failure! Address error")
        
        # Verify socket was reset
        self.assertIsNone(self.ag.socket)
    
    @patch('socket.socket')
    def test_set_antenna_timeout(self, mock_socket_class):
        """Test handling of timeout error."""
        # Configure mock to raise timeout
        mock_socket_class.return_value.connect.side_effect = socket.timeout("Test timeout")
        
        # Call method
        result = self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify callback was called with error message
        self.callback.assert_called_once_with("AG Comm Failure! Connection timeout")
        
        # Verify socket was reset
        self.assertIsNone(self.ag.socket)
    
    @patch('socket.socket')
    def test_set_antenna_connection_refused(self, mock_socket_class):
        """Test handling of connection refused error."""
        # Configure mock to raise connection refused
        mock_socket_class.return_value.connect.side_effect = ConnectionRefusedError("Test refused")
        
        # Call method
        result = self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify callback was called with error message
        self.callback.assert_called_once_with("AG Comm Failure! Connection refused")
        
        # Verify socket was reset
        self.assertIsNone(self.ag.socket)
    
    @patch('socket.socket')
    def test_set_antenna_no_callback(self, mock_socket_class):
        """Test antenna setting with no callback provided."""
        # Create AntennaGenius instance without callback
        ag = AntennaGenius()
        
        # Configure mock
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # Call method
        result = ag.set_antenna("192.168.1.100", 9007, "1", 5)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify socket operations
        mock_socket.settimeout.assert_called_once_with(0.5)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 9007))
        mock_socket.sendall.assert_called_once_with(b"C1|port set 1 band=5 \n")
        
        # Verify command counter incremented
        self.assertEqual(ag.command_counter, 1)


    @patch('socket.socket')
    def test_multiple_commands(self, mock_socket_class):
        """Test that multiple commands increment the counter."""
        # Configure mock
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # Call method multiple times
        self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
        self.ag.set_antenna("192.168.1.100", 9007, "1", 6)
        self.ag.set_antenna("192.168.1.100", 9007, "1", 7)
        
        # Verify socket reuse (connect only called once)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 9007))
        
        # Verify all commands were sent with incrementing counters
        expected_calls = [
            call(b"C1|port set 1 band=5 \n"),
            call(b"C2|port set 1 band=6 \n"),
            call(b"C3|port set 1 band=7 \n")
        ]
        mock_socket.sendall.assert_has_calls(expected_calls)
        
        # Verify final counter value
        self.assertEqual(self.ag.command_counter, 3)
    
    def test_counter_wrapping(self):
        """Test that the command counter wraps around at 100."""
        # Set counter to 99
        self.ag.command_counter = 99
        
        # Call set_antenna to increment counter
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket
            self.ag.set_antenna("192.168.1.100", 9007, "1", 5)
            
            # Verify counter wrapped to 0
            self.assertEqual(self.ag.command_counter, 0)
            
            # Verify correct command was sent
            mock_socket.sendall.assert_called_once_with(b"C0|port set 1 band=5 \n")
    
    def test_close(self):
        """Test socket close method."""
        # Create a mock socket
        mock_socket = MagicMock()
        self.ag.socket = mock_socket
        
        # Call close method
        self.ag.close()
        
        # Verify socket was closed
        mock_socket.close.assert_called_once()
        
        # Verify socket was reset
        self.assertIsNone(self.ag.socket)


if __name__ == '__main__':
    unittest.main()