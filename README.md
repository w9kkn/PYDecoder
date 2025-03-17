# PYDecoder - N1MM+ to AntennaGenius and FTDI BCD Translator

This program serves as a translator utility to convert radio frequency data in N1MM+ style UDP radio information broadcasts to both FTDI C232HM MPSSE GPIO USB cables and a 4O3A Antenna Genius.

The original intent for this program was to mimic the functionality of a FlexRadio 6000 series transceiver in passing band data to other devices. The current version works, but features are being added, and error handling is being matured.

It currently automatically detects all C232HM MPSSE interfaces to a computer, and treats them all the same. We expect to add support for SO2R soon, and to improve error handling.

## Building the Application

### Local Build (Windows)

1. Make sure you have Python 3.12+ installed
2. Install dependencies: `pip install -r requirements.txt`
3. Install PyInstaller: `pip install pyinstaller`
4. Build the executable: `pyinstaller --onefile --noconsole --name PYDecoder main.py`
5. The executable will be created in the `dist` directory

### Automated Windows Build with GitHub Actions

This repository is configured with GitHub Actions to automatically build a Windows executable when:
- Code is pushed to the main branch
- A pull request is opened against the main branch
- A new tag is pushed with the format `v*` (e.g., v1.0.0)
- The workflow is manually triggered from the GitHub UI

When a new tag is pushed, the executable will be automatically attached to a GitHub Release.

To download the latest build:
1. Go to the GitHub Actions tab
2. Select the most recent "Build Windows Executable" workflow run
3. Download the artifact from the "Artifacts" section

## Configuration

The application uses a JSON configuration file (`config.json`) to store settings. On first run, a default configuration will be created if none exists.

