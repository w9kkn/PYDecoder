"""Tests for band_helpers module."""

import unittest
from pydecoder.utils.band_helpers import get_bcd, get_ag_band, get_band_name

class TestBandHelpers(unittest.TestCase):
    """Tests for band helper functions."""
    
    def test_get_bcd(self):
        """Test BCD values for different frequency bands."""
        # Test specific frequencies for each band
        self.assertEqual(get_bcd(1830), 0b0001)  # 160m
        self.assertEqual(get_bcd(3750), 0b0010)  # 80m
        self.assertEqual(get_bcd(5350), 0b0000)  # 60m
        self.assertEqual(get_bcd(7150), 0b0011)  # 40m
        self.assertEqual(get_bcd(10125), 0b0100)  # 30m
        self.assertEqual(get_bcd(14200), 0b0101)  # 20m
        self.assertEqual(get_bcd(18100), 0b0110)  # 17m
        self.assertEqual(get_bcd(21300), 0b0111)  # 15m
        self.assertEqual(get_bcd(24900), 0b1000)  # 12m
        self.assertEqual(get_bcd(28500), 0b1001)  # 10m
        self.assertEqual(get_bcd(50125), 0b1010)  # 6m
        
        # Test edge cases
        self.assertEqual(get_bcd(1999), 0b0001)  # Upper edge of 160m
        self.assertEqual(get_bcd(2000), 0b0010)  # Lower edge of 80m
        self.assertEqual(get_bcd(60000), 0b0000)  # Beyond upper range
        self.assertEqual(get_bcd(0), 0b0001)  # Zero frequency
    
    def test_get_ag_band(self):
        """Test antenna port values for different frequency bands."""
        # Test specific frequencies for each band
        self.assertEqual(get_ag_band(1830), 1)  # 160m
        self.assertEqual(get_ag_band(3750), 2)  # 80m
        self.assertEqual(get_ag_band(5350), 11)  # 60m
        self.assertEqual(get_ag_band(7150), 3)  # 40m
        self.assertEqual(get_ag_band(10125), 4)  # 30m
        self.assertEqual(get_ag_band(14200), 5)  # 20m
        self.assertEqual(get_ag_band(18100), 6)  # 17m
        self.assertEqual(get_ag_band(21300), 7)  # 15m
        self.assertEqual(get_ag_band(24900), 8)  # 12m
        self.assertEqual(get_ag_band(28500), 9)  # 10m
        self.assertEqual(get_ag_band(50125), 10)  # 6m
        
        # Test edge cases
        self.assertEqual(get_ag_band(1999), 1)  # Upper edge of 160m
        self.assertEqual(get_ag_band(2000), 2)  # Lower edge of 80m
        self.assertEqual(get_ag_band(60000), 1)  # Beyond upper range
        self.assertEqual(get_ag_band(0), 1)  # Zero frequency
    
    def test_get_band_name(self):
        """Test band name lookup for different frequencies."""
        # Test specific frequencies for each band
        self.assertEqual(get_band_name(1830), "160m")
        self.assertEqual(get_band_name(3750), "80m")
        self.assertEqual(get_band_name(5350), "60m")
        self.assertEqual(get_band_name(7150), "40m")
        self.assertEqual(get_band_name(10125), "30m")
        self.assertEqual(get_band_name(14200), "20m")
        self.assertEqual(get_band_name(18100), "17m")
        self.assertEqual(get_band_name(21300), "15m")
        self.assertEqual(get_band_name(24900), "12m")
        self.assertEqual(get_band_name(28500), "10m")
        self.assertEqual(get_band_name(50125), "6m")
        
        # Test edge cases
        self.assertEqual(get_band_name(1999), "160m")  # Upper edge of 160m
        self.assertEqual(get_band_name(2000), "80m")  # Lower edge of 80m
        self.assertEqual(get_band_name(60000), "unknown")  # Beyond upper range
        self.assertEqual(get_band_name(0), "160m")  # Zero frequency

if __name__ == '__main__':
    unittest.main()