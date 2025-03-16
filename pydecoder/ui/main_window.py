"""Main application window for PYDecoder."""
import tkinter as tk
from tkinter import ttk

from pydecoder.devices.ftdi import FTDIDeviceManager
from pydecoder.networking.antenna_genius import AntennaGenius
from pydecoder.networking.n1mm import N1MMListener
from pydecoder.utils.band_helpers import get_bcd, get_ag_band, get_band_name
from pydecoder.config import load_settings, save_settings

class DecoderUI:
    """Main UI for the PYDecoder application."""
    
    def __init__(self):
        """Initialize the application UI."""
        self.window = tk.Tk()
        self.window.title("IP Band Decoder")
        
        # State variables
        self.is_on = True
        self.radio_freq = 0
        self.settings = load_settings()
        
        # Initialize components
        self.ftdi_manager = FTDIDeviceManager()
        self.antenna_genius = AntennaGenius(self.update_ag_status)
        self.n1mm_listener = N1MMListener()
        
        # Create UI
        self.create_tabs()
        self.create_freq_tab()
        self.create_bpf_tab()
        self.create_ag_tab()
        
        # Load settings into UI
        self.load_settings_to_ui()
        
        # Start polling
        self.window.after(100, self.freq_update)
    
    def create_tabs(self) -> None:
        """Create the tabbed interface."""
        self.tab_control = ttk.Notebook(self.window)
        
        self.tab1 = ttk.Frame(self.tab_control)  # Frequency tab
        self.tab2 = ttk.Frame(self.tab_control)  # AntennaGenius tab
        self.tab3 = ttk.Frame(self.tab_control)  # BPF control tab
        
        self.tab_control.add(self.tab1, text='Freq Data')
        self.tab_control.add(self.tab3, text='BPF Control')
        self.tab_control.add(self.tab2, text='4O3A Band Ports')
        
        self.tab_control.pack(expand=1, fill='both')
    
    def create_freq_tab(self) -> None:
        """Create the frequency data tab."""
        tk.Label(self.tab1, text="Logger IP Address:").grid(row=0)
        self.ipaddr = tk.Entry(self.tab1)
        self.ipaddr.grid(column=1, row=0)
        
        tk.Label(self.tab1, text="Logger UDP Port:").grid(row=1)
        self.udpport = tk.Entry(self.tab1)
        self.udpport.grid(column=1, row=1)
        
        tk.Label(self.tab1, text="Radio Freq:").grid(row=4)
        self.radfreq = tk.Label(self.tab1, text="Waiting for data...")
        self.radfreq.grid(column=1, row=4)
        
        self.on_button = tk.Button(
            self.tab1, 
            text="Start", 
            bd=0, 
            command=self.switch, 
            fg="green"
        )
        self.on_button.grid(row=3, column=1)
    
    def create_ag_tab(self) -> None:
        """Create the AntennaGenius tab."""
        tk.Label(self.tab2, text="IP Address:").grid(row=0)
        self.AG_IP = tk.Entry(self.tab2)
        self.AG_IP.grid(column=1, row=0)
        
        tk.Label(self.tab2, text="TCP Port:").grid(row=1)
        self.AG_TCP = tk.Entry(self.tab2)
        self.AG_TCP.grid(column=1, row=1)
        
        tk.Label(self.tab2, text="AG Port:").grid(row=2)
        self.AG_RF = tk.Entry(self.tab2)
        self.AG_RF.grid(column=1, row=2)
        
        self.ag_status = tk.Label(self.tab2, text="")
        self.ag_status.grid(row=3, column=0, columnspan=2)
    
    def create_bpf_tab(self) -> None:
        """Create the BPF Control tab."""
        tk.Label(self.tab3, text="FTDI Device URLs:").grid(row=0)
        
        device_urls = self.ftdi_manager.get_device_urls()
        for i, url in enumerate(device_urls):
            tk.Label(self.tab3, text=url).grid(row=i+1)
    
    def load_settings_to_ui(self) -> None:
        """Load settings from config into UI elements."""
        self.ipaddr.insert(0, self.settings["logger_ip"])
        self.udpport.insert(0, self.settings["logger_udp"])
        self.AG_IP.insert(0, self.settings["AG_1_IP"])
        self.AG_TCP.insert(0, self.settings["AG_1_UDP_Port"])
        self.AG_RF.insert(0, self.settings["AG_1_RF_Port"])
    
    def update_settings_from_ui(self) -> None:
        """Update settings from UI elements."""
        self.settings = {
            "logger_ip": self.ipaddr.get(),
            "logger_udp": self.udpport.get(),
            "AG_1_IP": self.AG_IP.get(),
            "AG_1_UDP_Port": self.AG_TCP.get(),
            "AG_1_RF_Port": self.AG_RF.get()
        }
    
    def switch(self) -> None:
        """Toggle the monitoring state."""
        if self.is_on:
            self.on_button.config(fg="red", text="Stop")
            self.is_on = False
        else:
            self.on_button.config(fg="green", text="Start")
            self.is_on = True
    
    def update_ag_status(self, message: str) -> None:
        """Update the AntennaGenius status message.
        
        Args:
            message: Status message to display
        """
        self.ag_status.config(text=message)
    
    def freq_update(self) -> None:
        """Poll for frequency updates and update devices."""
        self.update_settings_from_ui()
        
        if not self.is_on:
            try:
                # Set up N1MM listener if needed
                if not self.n1mm_listener.sock:
                    ip = self.settings["logger_ip"]
                    port = int(self.settings["logger_udp"])
                    self.n1mm_listener.setup_socket(ip, port)
                
                # Get radio data
                radio_dict = self.n1mm_listener.receive_data()
                
                if radio_dict and radio_dict.get("RadioInfo", {}).get("RadioNr") == "1":
                    freq = int(radio_dict["RadioInfo"]["Freq"]) / 100
                    self.radio_freq = freq
                    self.radfreq.config(text=f"{freq} kHz")
                    
                    # Update AntennaGenius
                    ag_ip = self.settings["AG_1_IP"]
                    ag_port = int(self.settings["AG_1_UDP_Port"])
                    ag_radio = self.settings["AG_1_RF_Port"]
                    ant_port = get_ag_band(self.radio_freq)
                    
                    self.antenna_genius.set_antenna(ag_ip, ag_port, ag_radio, ant_port)
                    
                    # Update FTDI devices
                    bcd_value = get_bcd(self.radio_freq)
                    self.ftdi_manager.write_bcd(bcd_value)
            except Exception as e:
                print(f"Error in freq_update: {e}")
        
        # Schedule next update
        self.window.after(500, self.freq_update)
    
    def run(self) -> None:
        """Run the application."""
        self.window.mainloop()
        
        # Save settings on exit
        save_settings(self.settings)


def main() -> None:
    """Entry point for the application when run as a module."""
    app = DecoderUI()
    app.run()