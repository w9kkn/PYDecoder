# UDP_Broadcast_to-_AntennaGenius_and_FTDI_BCD_Translater

This program serves as a translator utility to convert radio frequency data in N1MM+ style UDP radio information broadcasts to both FTDI C232HM MPSSE GPIO USB cables and a 4O3A Antenna Genius.

The origional intent for this program was to mimic the functionality of a FlexRadio 6000 series transciver in passing band data to other devices. The current version works, but features are being added, and error handling is being matured.

It currently automatically detects all C232HM MPSSE interfaces to a computer, and treats them all the same. We expect to add support for SO2R soon, and to improve error handling.

