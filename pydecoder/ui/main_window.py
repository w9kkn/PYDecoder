"""Main application window for PYDecoder."""
import logging
import tkinter as tk
from tkinter import ttk

from pydecoder.config import (
    load_settings, save_settings, 
    LOGGER_IP_KEY, LOGGER_UDP_KEY, AG_IP_KEY, 
    AG_TCP_PORT_KEY, AG_RF_PORT_KEY
)
from pydecoder.core.decoder_engine import DecoderEngine

logger = logging.getLogger(__name__)

class DecoderUI:
    """Main UI for the PYDecoder application.
    
    This class handles the creation and management of the user interface,
    delegating all business logic to the DecoderEngine class. It is responsible for:
    - Creating and managing the UI components
    - Handling user interactions
    - Displaying status updates and data to the user
    - Managing the application lifecycle
    """
    
    def __init__(self) -> None:
        """Initialize the application UI.
        
        Sets up the main window, initializes components, and creates the UI.
        """
        logger.info("Starting PYDecoder application")
        self.window = tk.Tk()
        self.window.title("IP Band Decoder")
        
        # Load settings
        self.settings = load_settings()
        
        # Initialize the engine with a status callback
        self.engine = DecoderEngine(self.settings, self.update_ag_status)
        
        # Create UI
        logger.info("Building user interface")
        self.create_tabs()
        self.create_freq_tab()
        self.create_bpf_tab()
        self.create_ag_tab()
        
        # Load settings into UI
        self.load_settings_to_ui()
        
        # Setup window close handler
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start polling
        self.window.after(100, self.freq_update)
    
    def create_tabs(self) -> None:
        """Create the tabbed interface.
        
        Creates a tabbed notebook with three tabs:
        - Freq Data: For N1MM logger configuration
        - BPF Control: For FTDI device control
        - 4O3A Band Ports: For AntennaGenius configuration
        """
        self.tab_control = ttk.Notebook(self.window)
        
        self.tab1 = ttk.Frame(self.tab_control)  # Frequency tab
        self.tab2 = ttk.Frame(self.tab_control)  # AntennaGenius tab
        self.tab3 = ttk.Frame(self.tab_control)  # BPF control tab
        
        self.tab_control.add(self.tab1, text='Freq Data')
        self.tab_control.add(self.tab3, text='BPF Control')
        self.tab_control.add(self.tab2, text='4O3A Band Ports')
        
        self.tab_control.pack(expand=1, fill='both')
    
    def create_freq_tab(self) -> None:
        """Create the frequency data tab.
        
        This tab contains fields for:
        - Logger IP Address: The IP address of the N1MM+ logger
        - Logger UDP Port: The UDP port for receiving radio information
        - Radio Freq: Displays the current radio frequency
        - Start/Stop Button: To control monitoring
        """
        tk.Label(self.tab1, text="Logger IP Address:").grid(row=0)
        self.logger_ip_entry = tk.Entry(self.tab1)
        self.logger_ip_entry.grid(column=1, row=0)
        
        tk.Label(self.tab1, text="Logger UDP Port:").grid(row=1)
        self.logger_port_entry = tk.Entry(self.tab1)
        self.logger_port_entry.grid(column=1, row=1)
        
        tk.Label(self.tab1, text="Radio Freq:").grid(row=4)
        self.radio_freq_label = tk.Label(self.tab1, text="Waiting for data...")
        self.radio_freq_label.grid(column=1, row=4)
        
        self.on_button = tk.Button(
            self.tab1, 
            text="Start", 
            bd=0, 
            command=self.switch, 
            fg="green"
        )
        self.on_button.grid(row=3, column=1)
    
    def create_ag_tab(self) -> None:
        """Create the AntennaGenius tab.
        
        This tab contains fields for:
        - IP Address: The IP address of the AntennaGenius device
        - TCP Port: The TCP port for the AntennaGenius device
        - AG Port: The RF port number for the AntennaGenius device
        - Status display for connection status
        """
        tk.Label(self.tab2, text="IP Address:").grid(row=0)
        self.ag_ip_entry = tk.Entry(self.tab2)
        self.ag_ip_entry.grid(column=1, row=0)
        
        tk.Label(self.tab2, text="TCP Port:").grid(row=1)
        self.ag_tcp_port_entry = tk.Entry(self.tab2)
        self.ag_tcp_port_entry.grid(column=1, row=1)
        
        tk.Label(self.tab2, text="AG Port:").grid(row=2)
        self.ag_rf_port_entry = tk.Entry(self.tab2)
        self.ag_rf_port_entry.grid(column=1, row=2)
        
        self.ag_status = tk.Label(self.tab2, text="")
        self.ag_status.grid(row=3, column=0, columnspan=2)
    
    def create_bpf_tab(self) -> None:
        """Create the BPF Control tab.
        
        This tab displays the list of detected FTDI devices with their URLs.
        These devices are used for BCD output to control band-pass filters.
        """
        tk.Label(self.tab3, text="FTDI Device URLs:").grid(row=0)
        
        device_urls = self.engine.get_device_urls()
        for i, url in enumerate(device_urls):
            tk.Label(self.tab3, text=url).grid(row=i+1)
    
    def load_settings_to_ui(self) -> None:
        """Load settings from config into UI elements.
        
        Populates the UI input fields with values from the settings dictionary.
        """
        self.logger_ip_entry.insert(0, self.settings[LOGGER_IP_KEY])
        self.logger_port_entry.insert(0, self.settings[LOGGER_UDP_KEY])
        self.ag_ip_entry.insert(0, self.settings[AG_IP_KEY])
        self.ag_tcp_port_entry.insert(0, self.settings[AG_TCP_PORT_KEY])
        self.ag_rf_port_entry.insert(0, self.settings[AG_RF_PORT_KEY])
    
    def update_settings_from_ui(self) -> None:
        """Update settings from UI elements.
        
        Updates the settings dictionary with current values from UI input fields.
        """
        self.settings = {
            LOGGER_IP_KEY: self.logger_ip_entry.get(),
            LOGGER_UDP_KEY: self.logger_port_entry.get(),
            AG_IP_KEY: self.ag_ip_entry.get(),
            AG_TCP_PORT_KEY: self.ag_tcp_port_entry.get(),
            AG_RF_PORT_KEY: self.ag_rf_port_entry.get()
        }
    
    def switch(self) -> None:
        """Toggle the monitoring state between active and inactive.
        
        When active, the application monitors for radio updates.
        When inactive, the application stops monitoring.
        
        The button color and text are updated to reflect the current state.
        """
        # Update settings first in case they changed
        self.update_settings_from_ui()
        
        # Update engine settings
        self.engine.settings = self.settings
        
        # Toggle monitoring state
        if self.engine.is_active:
            self.on_button.config(fg="green", text="Start")
            self.engine.stop_monitoring()
        else:
            self.on_button.config(fg="red", text="Stop")
            self.engine.start_monitoring()
    
    def update_ag_status(self, message: str) -> None:
        """Update the AntennaGenius status message.
        
        Args:
            message: Status message to display
        """
        self.ag_status.config(text=message)
    
    def freq_update(self) -> None:
        """Poll for frequency updates and update UI."""
        # Update frequency from engine
        new_freq = self.engine.update_frequency()
        
        # Update UI if we got a new frequency
        if new_freq is not None:
            self.radio_freq_label.config(text=f"{new_freq} kHz")
        
        # Schedule next update
        self.window.after(500, self.freq_update)
    
    def run(self) -> None:
        """Run the application."""
        logger.info("Starting main application loop")
        try:
            self.window.mainloop()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            # Cleanup happens in on_closing
            pass

    def on_closing(self) -> None:
        """Handle window close event.
        
        This method is called when the user closes the application window.
        It ensures resources are properly cleaned up before exiting.
        """
        logger.info("Window closing, cleaning up resources")
        
        # Save settings
        self.update_settings_from_ui()
        save_settings(self.settings)
            
        # Shutdown the engine
        self.engine.shutdown()
        
        # Destroy the window
        self.window.destroy()


def main() -> None:
    """Entry point for the application when run as a module."""
    app = DecoderUI()
    app.run()