"""
Peak detection for laser calibration.

Detects and localizes peaks in intensity profiles for wavelength calibration.
"""

import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Peak:
    """Detected peak information."""
    
    position: float  # Peak position (pixel or index)
    amplitude: float  # Peak amplitude
    prominence: float  # Peak prominence
    width: float  # Peak width
    confidence: float  # Confidence score [0, 1]


class PeakDetector:
    """Detect peaks in 1D intensity profiles."""
    
    def __init__(
        self,
        prominence: float = 0.1,
        width: Optional[Tuple[float, float]] = None,
        distance: Optional[float] = None,
        height: Optional[float] = None
    ):
        """
        Initialize peak detector.
        
        Args:
            prominence: Minimum peak prominence (relative to signal range)
            width: Tuple of (min_width, max_width) in pixels
            distance: Minimum distance between peaks
            height: Minimum peak height (absolute or relative)
        """
        self.prominence = prominence
        self.width = width
        self.distance = distance
        self.height = height
    
    def detect_peaks(
        self,
        intensity: np.ndarray,
        max_peaks: Optional[int] = None
    ) -> List[Peak]:
        """
        Detect peaks in intensity profile.
        
        Args:
            intensity: 1D intensity array
            max_peaks: Maximum number of peaks to return (None = all)
            
        Returns:
            List of detected peaks, sorted by prominence (highest first)
        """
        if len(intensity) < 3:
            return []
        
        # Normalize intensity to [0, 1] for relative thresholds
        intensity_norm = (intensity - np.min(intensity)) / (np.ptp(intensity) + 1e-10)
        
        # Calculate prominence threshold
        prominence_abs = self.prominence * np.ptp(intensity)
        
        # Find peaks
        peak_indices, properties = find_peaks(
            intensity,
            prominence=prominence_abs,
            width=self.width,
            distance=self.distance,
            height=self.height
        )
        
        if len(peak_indices) == 0:
            logger.info("No peaks detected")
            return []
        
        # Create Peak objects
        peaks = []
        for i, idx in enumerate(peak_indices):
            # Sub-pixel localization using parabolic interpolation
            refined_pos = self._refine_peak_position(intensity, idx)
            
            # Calculate confidence based on prominence and width
            prominence = properties['prominences'][i]
            width = properties['widths'][i]
            
            # Confidence: higher prominence = better, narrower = better (for laser peaks)
            confidence = min(1.0, prominence / (np.ptp(intensity) * 0.5))
            if width < 10:  # Narrow peak bonus
                confidence = min(1.0, confidence * 1.2)
            
            peak = Peak(
                position=refined_pos,
                amplitude=intensity[idx],
                prominence=prominence,
                width=width,
                confidence=confidence
            )
            peaks.append(peak)
        
        # Sort by prominence (descending)
        peaks.sort(key=lambda p: p.prominence, reverse=True)
        
        # Limit number of peaks
        if max_peaks is not None:
            peaks = peaks[:max_peaks]
        
        logger.info(f"Detected {len(peaks)} peaks")
        
        return peaks
    
    def _refine_peak_position(self, intensity: np.ndarray, idx: int) -> float:
        """
        Refine peak position using parabolic interpolation.
        
        Args:
            intensity: Intensity array
            idx: Initial peak index
            
        Returns:
            Refined peak position (sub-pixel)
        """
        # Need neighbors for interpolation
        if idx == 0 or idx == len(intensity) - 1:
            return float(idx)
        
        # Three points: left, center, right
        y1 = intensity[idx - 1]
        y2 = intensity[idx]
        y3 = intensity[idx + 1]
        
        # Parabolic interpolation
        # Vertex of parabola through three points
        denom = 2 * (y1 - 2*y2 + y3)
        if abs(denom) < 1e-10:
            return float(idx)
        
        offset = (y1 - y3) / denom
        
        # Refined position
        refined = idx + offset
        
        # Sanity check
        if abs(offset) > 1:
            return float(idx)
        
        return refined
    
    def fit_gaussian(
        self,
        intensity: np.ndarray,
        peak_position: float,
        window: int = 20
    ) -> Optional[Tuple[float, float, float]]:
        """
        Fit a Gaussian to a peak for more accurate localization.
        
        Args:
            intensity: Intensity array
            peak_position: Approximate peak position
            window: Fitting window size
            
        Returns:
            Tuple of (center, amplitude, sigma) or None if fit fails
        """
        # Extract window around peak
        idx = int(peak_position)
        start = max(0, idx - window // 2)
        end = min(len(intensity), idx + window // 2)
        
        if end - start < 5:
            return None
        
        x = np.arange(start, end)
        y = intensity[start:end]
        
        # Initial guess
        amp_guess = np.max(y)
        center_guess = x[np.argmax(y)]
        sigma_guess = 2.0
        
        # Gaussian function
        def gaussian(x, amp, center, sigma):
            return amp * np.exp(-(x - center)**2 / (2 * sigma**2))
        
        try:
            popt, _ = curve_fit(
                gaussian, x, y,
                p0=[amp_guess, center_guess, sigma_guess],
                maxfev=1000
            )
            return tuple(popt)
        except Exception as e:
            logger.debug(f"Gaussian fit failed: {e}")
            return None
