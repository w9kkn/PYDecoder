"""Utility functions for band and frequency calculations."""

def get_bcd(frequency: int) -> int:
    """Calculate BCD value for a given frequency.
    
    Args:
        frequency: Frequency in kHz
        
    Returns:
        int: BCD value corresponding to the frequency band
    """
    if frequency < 2000:
        return 0b0001  # 160m
    elif frequency < 4000:
        return 0b0010  # 80m
    elif frequency < 6000:
        return 0b0000  # 60m
    elif frequency < 8000:
        return 0b0011  # 40m
    elif frequency < 11000:
        return 0b0100  # 30m
    elif frequency < 15000:
        return 0b0101  # 20m
    elif frequency < 19000:
        return 0b0110  # 17m
    elif frequency < 22000:
        return 0b0111  # 15m
    elif frequency < 25000:
        return 0b1000  # 12m
    elif frequency < 30000:
        return 0b1001  # 10m
    elif frequency < 60000:
        return 0b1010  # 6m
    else:
        return 0b0000  # Default

def get_ag_band(frequency: int) -> int:
    """Calculate antenna port for a given frequency.
    
    Args:
        frequency: Frequency in kHz
        
    Returns:
        int: Antenna port number corresponding to the frequency band
    """
    if frequency < 2000:
        return 1  # 160m
    elif frequency < 4000:
        return 2  # 80m
    elif frequency < 6000:
        return 11  # 60m
    elif frequency < 8000:
        return 3  # 40m
    elif frequency < 11000:
        return 4  # 30m
    elif frequency < 15000:
        return 5  # 20m
    elif frequency < 19000:
        return 6  # 17m
    elif frequency < 22000:
        return 7  # 15m
    elif frequency < 25000:
        return 8  # 12m
    elif frequency < 30000:
        return 9  # 10m
    elif frequency < 60000:
        return 10  # 6m
    else:
        return 1  # Default

def get_band_name(frequency: int) -> str:
    """Get band name for a given frequency.
    
    Args:
        frequency: Frequency in kHz
        
    Returns:
        str: Band name (e.g., "160m", "80m")
    """
    if frequency < 2000:
        return "160m"
    elif frequency < 4000:
        return "80m"
    elif frequency < 6000:
        return "60m"
    elif frequency < 8000:
        return "40m"
    elif frequency < 11000:
        return "30m"
    elif frequency < 15000:
        return "20m"
    elif frequency < 19000:
        return "17m"
    elif frequency < 22000:
        return "15m"
    elif frequency < 25000:
        return "12m"
    elif frequency < 30000:
        return "10m"
    elif frequency < 60000:
        return "6m"
    else:
        return "unknown"