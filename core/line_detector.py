"""
Automatic detection of spectrum lines in images.

Uses computer vision techniques (edge detection, Hough transform)
to automatically locate spectrum lines.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LineResult:
    """Result from automatic line detection."""
    
    points: List[Tuple[int, int]]  # List of (x, y) points defining the line
    confidence: float  # Confidence score [0, 1]
    is_curved: bool  # Whether the line is curved
    angle: Optional[float] = None  # Angle in degrees (for straight lines)
    
    @property
    def is_straight(self) -> bool:
        """Whether this is a straight line."""
        return not self.is_curved and len(self.points) == 2


class AutoLineDetector:
    """Automatic detection of spectrum lines."""
    
    def __init__(
        self,
        canny_threshold1: int = 50,
        canny_threshold2: int = 150,
        hough_threshold: int = 50,
        min_line_length: int = 100,
        max_line_gap: int = 10,
        curvature_threshold: float = 0.1
    ):
        """
        Initialize line detector.
        
        Args:
            canny_threshold1: Canny lower threshold
            canny_threshold2: Canny upper threshold
            hough_threshold: Hough accumulator threshold
            min_line_length: Minimum line length
            max_line_gap: Maximum gap between line segments
            curvature_threshold: Threshold for detecting curved lines
        """
        self.canny_threshold1 = canny_threshold1
        self.canny_threshold2 = canny_threshold2
        self.hough_threshold = hough_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.curvature_threshold = curvature_threshold
    
    def detect(self, image: np.ndarray) -> Optional[LineResult]:
        """
        Detect spectrum line in image.
        
        Args:
            image: Input image (BGR or grayscale)
            
        Returns:
            LineResult if line found, None otherwise
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Try brightness-based detection first
        line_result = self._detect_by_brightness(gray, image)
        if line_result is not None and line_result.confidence > 0.5:
            return line_result
        
        # Fall back to edge-based detection
        line_result = self._detect_by_edges(gray)
        if line_result is not None:
            return line_result
        
        logger.warning("No spectrum line detected")
        return None
    
    def _detect_by_brightness(
        self,
        gray: np.ndarray,
        original: np.ndarray
    ) -> Optional[LineResult]:
        """
        Detect line based on brightness (brightest horizontal region).
        
        Args:
            gray: Grayscale image
            original: Original image (for confidence calculation)
            
        Returns:
            LineResult if successful, None otherwise
        """
        height, width = gray.shape
        
        # Find brightest horizontal band
        # Sum intensity horizontally
        horizontal_profile = np.mean(gray, axis=1)
        
        # Smooth the profile
        from scipy.ndimage import gaussian_filter1d
        smoothed_profile = gaussian_filter1d(horizontal_profile, sigma=height * 0.02)
        
        # Find peak
        peak_y = np.argmax(smoothed_profile)
        peak_value = smoothed_profile[peak_y]
        
        # Check if peak is significant
        mean_value = np.mean(smoothed_profile)
        if peak_value < mean_value * 1.2:
            # Not a strong enough peak
            return None
        
        #Determine thickness (FWHM - Full Width at Half Maximum)
        half_max = (peak_value + mean_value) / 2
        above_half = smoothed_profile > half_max
        
        # Find continuous region around peak
        y_min = peak_y
        while y_min > 0 and above_half[y_min]:
            y_min -= 1
        
        y_max = peak_y
        while y_max < height - 1 and above_half[y_max]:
            y_max += 1
        
        y_center = (y_min + y_max) // 2
        thickness = y_max - y_min
        
        # Check if this looks like a spectrum line (should be relatively thin)
        if thickness > height * 0.3:
            # Too thick, probably not a spectrum line
            return None
        
        # Create line points (horizontal line at y_center)
        points = [(0, y_center), (width - 1, y_center)]
        
        # Calculate confidence based on peak prominence
        confidence = min(1.0, (peak_value - mean_value) / mean_value)
        
        logger.info(f"Detected horizontal line at y={y_center}, confidence={confidence:.2f}")
        
        return LineResult(
            points=points,
            confidence=confidence,
            is_curved=False,
            angle=0.0
        )
    
    def _detect_by_edges(self, gray: np.ndarray) -> Optional[LineResult]:
        """
        Detect line using edge detection and Hough transform.
        
        Args:
            gray: Grayscale image
            
        Returns:
            LineResult if successful, None otherwise
        """
        # Edge detection
        edges = cv2.Canny(gray, self.canny_threshold1, self.canny_threshold2)
        
        # Hough Line Transform (probabilistic)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )
        
        if lines is None or len(lines) == 0:
            return None
        
        # Find the longest horizontal-ish line
        best_line = None
        best_length = 0
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # Prefer more horizontal lines (small angle)
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1))
            angle_deg = np.degrees(angle)
            
            # Prioritize horizontal lines (within 20 degrees)
            if angle_deg < 20 or angle_deg > 160:
                length_score = length * 1.5  # Bonus for horizontal
            else:
                length_score = length
            
            if length_score > best_length:
                best_length = length_score
                best_line = (x1, y1, x2, y2)
        
        if best_line is None:
            return None
        
        x1, y1, x2, y2 = best_line
        points = [(x1, y1), (x2, y2)]
        
        # Calculate angle
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        
        # Confidence based on length relative to image width
        width = gray.shape[1]
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        confidence = min(1.0, length / width)
        
        logger.info(f"Detected line via Hough: ({x1},{y1})->({x2},{y2}), angle={angle:.1f}°")
        
        return LineResult(
            points=points,
            confidence=confidence,
            is_curved=False,
            angle=angle
        )
    
    def refine_line(
        self,
        image: np.ndarray,
        initial_line: LineResult
    ) -> LineResult:
        """
        Refine detected line to better fit the spectrum.
        
        Args:
            image: Input image
            initial_line: Initial line detection result
            
        Returns:
            Refined line result
        """
        # For now, just return the initial line
        # TODO: Implement refinement (e.g., fit to brightness centroid)
        return initial_line
