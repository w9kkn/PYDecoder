"""Tests for N1MMListener class."""

import socket
import unittest
from unittest.mock import Mock, patch, MagicMock, call

from pydecoder.networking.n1mm import N1MMListener


class TestN1MMListener(unittest.TestCase):
    """Test cases for N1MMListener functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.listener = N1MMListener()
    
    def test_init(self):
        """Test initialization."""
        self.assertIsNone(self.listener.sock)
    
    @patch('socket.socket')
    def test_setup_socket_success(self, mock_socket_class):
        """Test successful socket setup."""
        # Configure mock
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        # Call method
        result = self.listener.setup_socket("127.0.0.1", 12345)
        
        # Verify result
        self.assertTrue(result)
        
        # Verify socket was set up correctly
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_socket.settimeout.assert_called_once_with(5)
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 12345))
        
        # Verify socket was stored
        self.assertEqual(self.listener.sock, mock_socket)
    
    @patch('socket.socket')
    def test_setup_socket_failure(self, mock_socket_class):
        """Test handling of socket setup failure."""
        # Configure mock to raise error
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.bind.side_effect = socket.error("Test error")
        
        # Call method
        result = self.listener.setup_socket("127.0.0.1", 12345)
        
        # Verify result
        self.assertFalse(result)
        
        # Verify socket was attempted to be set up
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_socket.settimeout.assert_called_once_with(5)
        mock_socket.bind.assert_called_once_with(("127.0.0.1", 12345))
    
    def test_receive_data_no_socket(self):
        """Test receive_data when no socket is set up."""
        # Call method
        result = self.listener.receive_data()
        
        # Verify result
        self.assertIsNone(result)
    
    def test_receive_data_timeout(self):
        """Test handling of socket timeout."""
        # Set up mock socket
        self.listener.sock = Mock()
        self.listener.sock.recvfrom.side_effect = socket.timeout("Test timeout")
        
        # Call method
        result = self.listener.receive_data()
        
        # Verify result
        self.assertIsNone(result)
        
        # Verify socket was used correctly
        self.listener.sock.recvfrom.assert_called_once_with(2048)
    
    def test_receive_data_success(self):
        """Test successful data reception and parsing."""
        # XML test data
        xml_data = """<RadioInfo>
            <RadioNr>1</RadioNr>
            <Freq>1415000</Freq>
            <TXFreq>1415000</TXFreq>
            <Mode>USB</Mode>
            <OpCall>W9KKN</OpCall>
        </RadioInfo>""".encode('utf-8')
        
        # Set up mock socket
        self.listener.sock = Mock()
        self.listener.sock.recvfrom.return_value = (xml_data, ("127.0.0.1", 12345))
        
        # Call method
        result = self.listener.receive_data()
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result["RadioInfo"]["RadioNr"], "1")
        self.assertEqual(result["RadioInfo"]["Freq"], "1415000")
        
        # Verify socket was used correctly
        self.listener.sock.recvfrom.assert_called_once_with(2048)
    
    def test_close(self):
        """Test socket closing."""
        # Set up mock socket
        self.listener.sock = Mock()
        
        # Call method
        self.listener.close()
        
        # Verify socket was closed
        self.listener.sock.close.assert_called_once()
        
        # Verify socket reference was cleared
        self.assertIsNone(self.listener.sock)
    
    def test_close_no_socket(self):
        """Test that close() is safe when no socket exists."""
        # Ensure no socket
        self.listener.sock = None
        
        # Call method (should not raise exception)
        self.listener.close()


if __name__ == '__main__':
    unittest.main()