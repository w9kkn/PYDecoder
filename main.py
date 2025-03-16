#!/usr/bin/env python3
"""
PYDecoder - UDP Broadcast to AntennaGenius and FTDI BCD Translator

This program serves as a translator utility to convert radio frequency data
in N1MM+ style UDP radio information broadcasts to both FTDI C232HM MPSSE
GPIO USB cables and a 4O3A Antenna Genius.
"""

from pydecoder.ui.main_window import DecoderUI

if __name__ == "__main__":
    # Create and run the application
    app = DecoderUI()
    app.run()