# Spectrum Analyzer

A production-grade Python application for spectrum analysis with modern PySide6 GUI. Designed for analyzing optical spectra from images and live video feeds with wavelength calibration support.

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **Static Image Analysis**: Load and analyze spectrum images (PNG, JPG, WebP)
- **Live Video Mode**: Real-time spectrum analysis from camera feeds
- **Wavelength Calibration**: Polynomial fitting with known laser wavelengths
- **Automatic Line Detection**: Computer vision-based spectrum line detection
- **Manual Line Selection**: Draw custom sampling lines
- **Interactive Graphing**: matplotlib integration with spectrum strip overlay
- **Color Integrity**: Proper linear RGB processing preserves spectral colors
- **Modern Dark UI**: Clean, professional interface with PySide6

## Installation

### Requirements

- Python 3.10 or higher
- Pip package manager

### Setup

1. **Clone or navigate to the repository**:
   ```bash
   cd /home/ahmed/dev/Python/Spectrometer
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

1. **Launch the application**:
   ```bash
   python main.py
   ```

2. **Analyze a spectrum image**:
   - Go to the "Static Image Analysis" tab
   - Click "Open Image" and select a spectrum image
   - Choose detection mode:
     - **Automatic**: App detects the spectrum line automatically
     - **Manual**: Draw a line across the spectrum
   - Click "Analyze Spectrum"
   - View the intensity graph with color strip overlay

3. **Calibrate wavelengths**:
   - Go to the "Calibration" tab
   - Load a spectrum with known laser lines
   - Click "Detect Peaks" to find laser peaks
   - Enter the known wavelength for each peak  - Click "Add Point" to add calibration points
   - Repeat for at least 2 known wavelengths
   - Click "Fit Calibration"
   - Save your calibration profile for reuse

4. **Live video mode**:
   - Go to the "Live Video Mode" tab
   - Click "Connect Camera"
   - Enter camera index (usually 0 for built-in webcam)
   - Real-time spectrum analysis will begin

## Usage Guide

### Static Image Analysis

The static analysis tab allows you to analyze spectrum images:

1. **Open Image**: Load a spectrum image file
2. **Detection Mode**:
   - **Manual**: Draw a line across the visible spectrum
   - **Automatic**: App automatically detects the brightest horizontal line
3. **Adjust Parameters** (Inspector Panel):
   - **Thickness**: Width of sampling region (1-20 pixels)
   - **Smoothing**: Noise reduction strength (0-100%)
   - **Background Removal**: Remove dark background (0-100%)
4. **Analyze**: Extracts 1D intensity profile
5. **Graph Display**:
   - Shows intensity vs pixel position (or wavelength if calibrated)
   - Color strip aligned above graph
   - Hover to highlight corresponding wavelengths
   - Toggle raw/smoothed curves
   - Switch between linear/log scale

### Wavelength Calibration

Calibration maps pixel positions to wavelengths using known laser peaks:

**Procedure**:
1. Capture spectrum with known laser wavelengths (e.g., 405nm, 532nm, 650nm)
2. Open the image in Static Analysis tab
3. Analyze to extract intensity profile
4. Switch to Calibration tab
5. Click "Detect Peaks" – app finds prominent peaks
6. For each detected peak:
   - Note the pixel position
   - Enter the known wavelength
   - Click "Add Point"
7. After adding ≥2 points, click "Fit Calibration"
8. Review fit quality (R², RMSE)
9. Save profile for future use

**Polynomial Orders**:
- **Linear (order 1)**: Simple spectrometers with linear dispersion
- **Quadratic (order 2)**: Most spectrometers (default)
- **Cubic (order 3)**: High-precision or wide-range spectrometers

### Live Video Mode

Analyze spectra in real-time from a camera feed:

1. **Connect Camera**:
   - Click "Connect Camera"
   - Enter camera index (0 = default webcam, 1+ = external cameras)
   - For network streams, enter RTSP/HTTP URL
   
2. **Temporal Smoothing**: Adjust in Inspector Panel to reduce frame-to-frame noise

3. **Freeze Frame**: Capture and hold current frame for detailed analysis

### Inspector Panel Controls

The right-side panel provides real-time processing controls:

- **Line Selection Mode**: Manual or Automatic
- **Thickness**: Sampling region width
- **Smoothing**: Gaussian/median filtering strength
- **Background Removal**: Remove non-spectrum regions
- **Show Smoothed Curve**: Toggle Savitzky-Golay smoothed plot
- **Y-Scale**: Linear or Logarithmic
- **Smoothing Window**: Savitzky-Golay window size

## Mobile Camera Setup

### Option 1: DroidCam / IP Webcam (Recommended)

1. **Install app on mobile**:
   - Android: [DroidCam](https://play.google.com/store/apps/details?id=com.dev47apps.droidcam) or [IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)
   - iOS: [EpocCam](https://apps.apple.com/app/epoccam-webcamera-for-computer/id449133483)

2. **Connect same WiFi network** as your computer

3. **Start streaming** in the app – note the IP address shown

4. **In Spectrum Analyzer**:
   - Live Video Mode → Connect Camera
   - Enter stream URL (shown in mobile app)
   - Example: `http://192.168.1.100:8080/video`

### Option 2: USB Webcam

Simply connect any USB webcam and use camera index 0, 1, or 2.

### Option 3: ADB USB Debugging (Advanced)

Requires Android SDK and ADB setup. See online guides for `adb forward` port tunneling.

## Architecture

```
Spectrometer/
├── main.py                 # Application entry point
├── core/                   # Image processing algorithms
│   ├── spectrum_sampler.py # 1D cross-section extraction
│   ├── line_detector.py    # Automatic line detection
│   └── image_processor.py  # Smoothing, background removal
├── calibration/            # Wavelength mapping
│   ├── calibration_model.py# Polynomial fitting
│   ├── peak_detector.py    # Laser peak detection
│   └── profile_manager.py  # Save/load profiles
├── video/                  # Live capture
│   ├── video_manager.py    # Camera feed handling
│   └── frame_processor.py  # Temporal smoothing
├── ui/                     # PySide6 GUI
│   ├── main_window.py      # Main window
│   ├── widgets/            # Custom widgets
│   └── styles/             # Qt stylesheets
└── utils/                  # Utilities
    ├── error_handler.py    # Error handling
    ├── logger.py           # Logging
    ├── color_utils.py      # Color conversions
    └── config_manager.py   # Configuration
```

## Key Technical Features

### Color Integrity

- **Linear RGB Processing**: All intensity calculations use proper gamma-corrected linear RGB
- **ITU-R BT.709 Weights**: Photometrically accurate luminance conversion
- **No Saturation Modification**: Background removal preserves color fidelity
- **Perpendicular Averaging**: Cross-section samples are averaged, not summed

### Automatic Line Detection

- **Brightness-based**: Finds brightest horizontal region
- **Hough Transform**: Fallback edge-based detection
- **Handles Tilted Spectra**: Detects non-horizontal lines
- **Curved Spectrum Support**: Polyline approximation (planned enhancement)

### Calibration System

- **Polynomial Fitting**: 1st to 3rd order polynomials
- **Fit Quality Metrics**: R², RMSE, maximum error
- **Sub-pixel Localization**: Parabolic interpolation for peak positions
- **Profile Management**: Save/load/export calibration profiles

## Troubleshooting

### "No spectrum detected"
- Ensure the spectrum is clearly visible and bright
- Try Manual mode and draw the line yourself
- Increase image contrast before loading
- Check that the spectrum is roughly horizontal

### Camera won't connect
- Check camera permissions
- Verify camera index (try 0, 1, 2...)
- Close other apps using the camera
- For network streams, verify IP address and port

### Poor calibration fit (low R²)
- Use more calibration points (3+ recommended)
- Ensure known wavelengths are accurate
- Check for peak detection errors
- Try different polynomial order

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

- Follows PEP 8
- Type hints throughout
- Comprehensive docstrings
- Google-style docstring format

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Acknowledgments

- Built with [PySide6](https://www.qt.io/qt-for-python)
- Image processing with [OpenCV](https://opencv.org/)
- Plotting with [matplotlib](https://matplotlib.org/)
- Scientific computing with [NumPy](https://numpy.org/) and [SciPy](https://scipy.org/)

---

**Version**: 1.0.0  
**Author**: Spectrum Analysis Team  
**Last Updated**: 2025-12-02
