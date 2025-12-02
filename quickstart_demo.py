"""
Quick start guide script.

Demonstrates basic usage of the spectrum analyzer programmatically.
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt

from core import SpectrumSampler, AutoLineDetector
from calibration import CalibrationModel
from utils import setup_logger, bgr_to_linear_rgb


def main():
    """Demonstrate basic usage."""
    
    # Set up logging
    setup_logger("quickstart", level=20)
    
    print("Spectrum Analyzer - Quick Start Demo")
    print("=" * 50)
    
    # Create synthetic spectrum image for demo
    print("\n1. Creating synthetic spectrum image...")
    spectrum_image = create_synthetic_spectrum()
    cv2.imwrite("samples/synthetic_spectrum.png", spectrum_image)
    print("   Saved to: samples/synthetic_spectrum.png")
    
    # Detect spectrum line
    print("\n2. Detecting spectrum line...")
    detector = AutoLineDetector()
    line_result = detector.detect(spectrum_image)
    
    if line_result:
        print(f"   Found line with confidence: {line_result.confidence:.2f}")
        print(f"   Line points: {line_result.points}")
    else:
        print("   Using default horizontal line")
        h, w = spectrum_image.shape[:2]
        line_result = type('obj', (object,), {
            'points': [(0, h//2), (w-1, h//2)]
        })
    
    # Extract spectrum
    print("\n3. Extracting intensity profile...")
    sampler = SpectrumSampler()    
    pixel_positions, intensity = sampler.extract_cross_section(
        spectrum_image,
        line_result.points,
        thickness=5
    )
    print(f"   Extracted {len(intensity)} points")
    
    # Create calibration (example with synthetic known points)
    print("\n4. Creating calibration...")
    calibration = CalibrationModel()
    
    # Simulate known laser peaks
    calibration.add_point(100, 450)   # Blue
    calibration.add_point(250, 550)   # Green
    calibration.add_point(400, 650)   # Red
    
    if calibration.fit():
        quality = calibration.get_fit_quality()
        print(f"   Calibration R²: {quality['r_squared']:.4f}")
        print(f"   RMSE: {quality['rmse']:.2f} nm")
        
        # Convert to wavelengths
        wavelengths = calibration.pixel_to_wavelength(pixel_positions)
        print(f"   Wavelength range: {wavelengths[0]:.1f} - {wavelengths[-1]:.1f} nm")
    
    # Plot results
    print("\n5. Plotting results...")
    plt.figure(figsize=(12, 4))
    
    if calibration.is_fitted():
        plt.plot(wavelengths, intensity, 'b-', linewidth=2)
        plt.xlabel('Wavelength (nm)')
    else:
        plt.plot(pixel_positions, intensity, 'b-', linewidth=2)
        plt.xlabel('Pixel Position')
    
    plt.ylabel('Intensity')
    plt.title('Spectrum Intensity Profile')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('samples/spectrum_plot.png', dpi=150)
    print("   Saved plot to: samples/spectrum_plot.png")
    
    print("\n" + "=" * 50)
    print("Demo complete! Check the samples/ directory for outputs.")
    print("\nTo launch the GUI application, run:")
    print("    python main.py")


def create_synthetic_spectrum(width=500, height=100):
    """
    Create a synthetic spectrum image for demonstration.
    
    Returns:
        BGR image with rainbow gradient
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    for x in range(width):
        # Create rainbow gradient
        hue = int(180 * x / width)  # HSV hue (0-180 in OpenCV)
        color = cv2.cvtColor(
            np.uint8([[[hue, 255, 255]]]),
            cv2.COLOR_HSV2BGR
        )[0, 0]
        
        # Make it a horizontal band in the middle
        y_start = height // 3
        y_end = 2 * height // 3
        image[y_start:y_end, x] = color
    
    # Add some Gaussian noise for realism
    noise = np.random.normal(0, 5, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return image


if __name__ == "__main__":
    main()
