"""Core decoder engine that manages the business logic of the application."""
import logging
from typing import Dict, Any, Callable, Optional

from pydecoder.config import (
    LOGGER_IP_KEY, LOGGER_UDP_KEY, AG_IP_KEY, 
    AG_TCP_PORT_KEY, AG_RF_PORT_KEY
)
from pydecoder.devices.ftdi import FTDIDeviceManager
from pydecoder.networking.antenna_genius import AntennaGenius
from pydecoder.networking.n1mm import N1MMListener
from pydecoder.utils.band_helpers import get_bcd, get_ag_band, get_band_name

logger = logging.getLogger(__name__)

class DecoderEngine:
    """Core engine for the PYDecoder application.
    
    This class manages the business logic of the application, handling:
    - Device management (FTDI)
    - Network communication (N1MM, AntennaGenius)
    - Frequency processing and band determination
    
    It is designed to be used by any UI implementation and contains
    no UI-specific code.
    """
    
    def __init__(
        self, 
        settings: Dict[str, Any], 
        status_callback: Optional[Callable[[str], None]] = None,
        simulation_mode: bool = False
    ) -> None:
        """Initialize the decoder engine.
        
        Args:
            settings: Application settings dictionary
            status_callback: Optional callback for status updates
            simulation_mode: If True, runs FTDI in simulation mode (no actual hardware access)
        """
        logger.info("Initializing decoder engine")
        
        # State
        self.settings = settings
        self.is_active = False
        self.radio_freq = 0
        self.simulation_mode = simulation_mode
        
        # Check if simulation mode is forced via settings
        if settings.get("enable_simulation_mode", False):
            self.simulation_mode = True
            logger.info("Simulation mode enabled via settings")
        elif "enable_simulation_mode" in settings:
            logger.debug(f"Simulation mode setting found in config: {settings['enable_simulation_mode']}")
        
        # Initialize components
        logger.info("Initializing device manager")
        self.ftdi_manager = FTDIDeviceManager(simulation_mode=self.simulation_mode)
        
        logger.info("Initializing AntennaGenius client")
        self.antenna_genius = AntennaGenius(status_callback)
        
        logger.info("Initializing N1MM listener")
        self.n1mm_listener = N1MMListener()
    
    def start_monitoring(self) -> None:
        """Start monitoring for frequency updates."""
        self.is_active = True
        logger.info("Monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring for frequency updates."""
        self.is_active = False
        logger.info("Monitoring stopped")
    
    def update_frequency(self) -> Optional[float]:
        """Update frequency from N1MM, update devices if needed.
        
        This method should be called periodically to:
        1. Check for new radio data from N1MM
        2. Update the antenna and FTDI devices based on the new frequency
        
        Returns:
            Optional[float]: The new frequency if updated, None otherwise
        """
        if not self.is_active:
            return None
            
        try:
            # Set up N1MM listener if needed
            if not self.n1mm_listener.sock:
                logger_ip = self.settings[LOGGER_IP_KEY]
                try:
                    logger_port = int(self.settings[LOGGER_UDP_KEY])
                except ValueError as e:
                    logger.error(f"Invalid UDP port value: {self.settings[LOGGER_UDP_KEY]} - {e}")
                    logger_port = 12060  # Default to a sensible value
                
                success = self.n1mm_listener.setup_socket(logger_ip, logger_port)
                if not success:
                    logger.warning("Failed to set up N1MM listener, will retry")
                    return None
            
            # Get radio data
            radio_dict = self.n1mm_listener.receive_data()
            
            if radio_dict and radio_dict.get("RadioInfo", {}).get("RadioNr") == "1":
                try:
                    # Parse frequency data
                    freq_string = radio_dict["RadioInfo"]["Freq"]
                    freq = int(freq_string) / 100
                    self.radio_freq = freq
                    logger.debug(f"Radio frequency updated: {freq} kHz")
                    
                    # Update AntennaGenius
                    ag_ip_address = self.settings[AG_IP_KEY]
                    try:
                        ag_tcp_port = int(self.settings[AG_TCP_PORT_KEY])
                    except ValueError:
                        logger.error(f"Invalid AG port value: {self.settings[AG_TCP_PORT_KEY]}")
                        ag_tcp_port = 9007  # Default value
                        
                    ag_radio_number = self.settings[AG_RF_PORT_KEY]
                    antenna_port = get_ag_band(int(self.radio_freq))
                    
                    self.antenna_genius.set_antenna(ag_ip_address, ag_tcp_port, ag_radio_number, antenna_port)
                    
                    # Update FTDI devices
                    bcd_value = get_bcd(int(self.radio_freq))
                    self.ftdi_manager.write_bcd(bcd_value)
                    
                    return freq
                except KeyError as e:
                    logger.error(f"Missing key in radio data: {e}")
                except ValueError as e:
                    logger.error(f"Invalid data format in radio data: {e}")
        except KeyError as e:
            logger.error(f"Missing configuration key: {e}")
        except ValueError as e:
            logger.error(f"Invalid value in configuration: {e}")
        except TypeError as e:
            logger.error(f"Type error in frequency update: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in frequency update: {e}", exc_info=True)
            
        return None
    
    def shutdown(self) -> None:
        """Release resources and prepare for shutdown."""
        logger.info("Shutting down decoder engine")
        
        # Close N1MM socket
        if self.n1mm_listener.sock:
            logger.info("Closing N1MM listener socket")
            self.n1mm_listener.close()
            
        # Close FTDI devices
        logger.info("Closing FTDI devices")
        self.ftdi_manager.close()
    
    def get_current_band(self) -> str:
        """Get the current band name based on frequency.
        
        Returns:
            str: Band name (e.g. "40m", "20m")
        """
        return get_band_name(self.radio_freq)
    
    def get_current_frequency(self) -> float:
        """Get the current radio frequency.
        
        Returns:
            float: Current frequency in kHz
        """
        return self.radio_freq
    
    def get_device_urls(self) -> list:
        """Get list of connected FTDI device URLs.
        
        Returns:
            list: List of FTDI device URLs
        """
        return self.ftdi_manager.get_device_urls()