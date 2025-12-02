"""
Spectrum sampling - extract 1D intensity cross-section from spectrum images.

CRITICAL: Preserves color integrity by using linear RGB for intensity calculations.
Averages perpendicular to the line, does not sum.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from scipy.ndimage import map_coordinates
from scipy.signal import savgol_filter
import logging

from utils.color_utils import bgr_to_linear_rgb, rgb_to_intensity

logger = logging.getLogger(__name__)


class SpectrumSampler:
    """Extract 1D intensity profiles from spectrum images."""
    
    def __init__(self):
        """Initialize spectrum sampler."""
        pass
    
    def extract_cross_section(
        self,
        image: np.ndarray,
        line_points: List[Tuple[int, int]],
        thickness: int = 5,
        smoothing: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract 1D intensity cross-section along a line.
        
        CRITICAL: This preserves color integrity:
        - Converts BGR to linear RGB
        - Averages perpendicular to line (not sum)
        - Uses proper photometric weights for intensity
        
        Args:
            image: Input image (BGR format from OpenCV)
            line_points: List of (x, y) points defining the line
                        Can be 2 points (straight) or multiple (curved)
            thickness: Sampling thickness perpendicular to line (pixels)
            smoothing: Optional Savitzky-Golay smoothing window size
            
        Returns:
            Tuple of (pixel_positions, intensity_values)
            - pixel_positions: x-coordinates along the line
            - intensity_values: intensity at each position
        """
        if len(line_points) < 2:
            raise ValueError("Need at least 2 points to define a line")
        
        # Convert to linear RGB for proper intensity calculation
        linear_rgb = bgr_to_linear_rgb(image)
        
        if len(line_points) == 2:
            # Straight line
            intensity = self._sample_straight_line(
                linear_rgb, line_points[0], line_points[1], thickness
            )
            pixel_positions = np.arange(len(intensity))
        else:
            # Polyline (curved spectrum)
            intensity, pixel_positions = self._sample_polyline(
                linear_rgb, line_points, thickness
            )
        
        # Optional smoothing
        if smoothing is not None and smoothing > 0:
            window_size = min(smoothing, len(intensity))
            if window_size % 2 == 0:
                window_size -= 1
            if window_size >= 3:
                intensity = savgol_filter(intensity, window_size, 2)
        
        return pixel_positions, intensity
    
    def _sample_straight_line(
        self,
        image: np.ndarray,
        point1: Tuple[int, int],
        point2: Tuple[int, int],
        thickness: int
    ) -> np.ndarray:
        """
        Sample intensity along a straight line.
        
        Args:
            image: Linear RGB image
            point1: Start point (x, y)
            point2: End point (x, y)
            thickness: Sampling thickness
            
        Returns:
            1D intensity array
        """
        x1, y1 = point1
        x2, y2 = point2
        
        # Line length
        length = int(np.sqrt((x2 - x1)**2 + (y2 - y1)**2))
        
        if length == 0:
            return np.array([])
        
        # Sample points along the line
        t = np.linspace(0, 1, length)
        x_line = x1 + t * (x2 - x1)
        y_line = y1 + t * (y2 - y1)
        
        # Perpendicular direction (normalized)
        dx = x2 - x1
        dy = y2 - y1
        norm = np.sqrt(dx**2 + dy**2)
        perp_x = -dy / norm  # Perpendicular vector
        perp_y = dx / norm
        
        # Sample perpendicular to the line
        half_thickness = thickness / 2.0
        offsets = np.linspace(-half_thickness, half_thickness, thickness)
        
        # Convert to intensity if RGB
        if len(image.shape) == 3:
            intensity_image = rgb_to_intensity(image)
        else:
            intensity_image = image
        
        # Sample at each point along the line
        intensity_profile = []
        
        for i in range(length):
            # Points perpendicular to line at this position
            x_perp = x_line[i] + offsets * perp_x
            y_perp = y_line[i] + offsets * perp_y
            
            # Sample using bilinear interpolation
            sampled_values = map_coordinates(
                intensity_image,
                [y_perp, x_perp],
                order=1,
                mode='nearest'
            )
            
            # Average (not sum!) across thickness
            avg_intensity = np.mean(sampled_values)
            intensity_profile.append(avg_intensity)
        
        return np.array(intensity_profile)
    
    def _sample_polyline(
        self,
        image: np.ndarray,
        line_points: List[Tuple[int, int]],
        thickness: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sample intensity along a polyline (curved spectrum).
        
        Args:
            image: Linear RGB image
            line_points: List of points defining the curve
            thickness: Sampling thickness
            
        Returns:
            Tuple of (pixel_positions, intensity_values)
        """
        # Sample each segment and concatenate
        all_intensities = []
        cumulative_length = 0
        pixel_positions = []
        
        for i in range(len(line_points) - 1):
            point1 = line_points[i]
            point2 = line_points[i + 1]
            
            # Sample this segment
            segment_intensity = self._sample_straight_line(
                image, point1, point2, thickness
            )
            
            # Track positions
            segment_positions = cumulative_length + np.arange(len(segment_intensity))
            
            all_intensities.append(segment_intensity)
            pixel_positions.append(segment_positions)
            
            cumulative_length += len(segment_intensity)
        
        # Concatenate all segments
        intensity = np.concatenate(all_intensities)
        positions = np.concatenate(pixel_positions)
        
        return intensity, positions
    
    def extract_color_strip(
        self,
        image: np.ndarray,
        line_points: List[Tuple[int, int]],
        thickness: int = 5,
        strip_height: int = 20
    ) -> np.ndarray:
        """
        Extract a color strip image along the line for display.
        
        This creates the visual spectrum strip shown above/below the graph.
        
        Args:
            image: Input image (BGR)
            line_points: Line points
            thickness: Sampling thickness
            strip_height: Height of output strip
            
        Returns:
            Color strip image (H x W x 3)
        """
        if len(line_points) == 2:
            # Straight line
            strip = self._extract_strip_straight(
                image, line_points[0], line_points[1], thickness, strip_height
            )
        else:
            # Polyline
            strip = self._extract_strip_polyline(
                image, line_points, thickness, strip_height
            )
        
        return strip
    
    def _extract_strip_straight(
        self,
        image: np.ndarray,
        point1: Tuple[int, int],
        point2: Tuple[int, int],
        thickness: int,
        strip_height: int
    ) -> np.ndarray:
        """Extract color strip for straight line."""
        x1, y1 = point1
        x2, y2 = point2
        
        # Line length
        length = int(np.sqrt((x2 - x1)**2 + (y2 - y1)**2))
        
        if length == 0:
            return np.zeros((strip_height, 1, 3), dtype=np.uint8)
        
        # Sample points along the line
        t = np.linspace(0, 1, length)
        x_line = x1 + t * (x2 - x1)
        y_line = y1 + t * (y2 - y1)
        
        # Perpendicular direction
        dx = x2 - x1
        dy = y2 - y1
        norm = np.sqrt(dx**2 + dy**2)
        perp_x = -dy / norm
        perp_y = dx / norm
        
        # Sample thickness
        half_thickness = thickness / 2.0
        offsets = np.linspace(-half_thickness, half_thickness, thickness)
        
        # Create strip
        strip = np.zeros((strip_height, length, 3), dtype=np.uint8)
        
        for i in range(length):
            # Sample perpendicular
            x_perp = x_line[i] + offsets * perp_x
            y_perp = y_line[i] + offsets * perp_y
            
            # Sample each color channel
            for c in range(3):
                sampled = map_coordinates(
                    image[:, :, c],
                    [y_perp, x_perp],
                    order=1,
                    mode='nearest'
                )
                avg_color = np.mean(sampled)
                strip[:, i, c] = int(avg_color)
        
        return strip
    
    def _extract_strip_polyline(
        self,
        image: np.ndarray,
        line_points: List[Tuple[int, int]],
        thickness: int,
        strip_height: int
    ) -> np.ndarray:
        """Extract color strip for polyline."""
        # Sample each segment and concatenate horizontally
        strips = []
        
        for i in range(len(line_points) - 1):
            segment_strip = self._extract_strip_straight(
                image, line_points[i], line_points[i + 1],
                thickness, strip_height
            )
            strips.append(segment_strip)
        
        # Concatenate horizontally
        full_strip = np.concatenate(strips, axis=1)
        
        return full_strip
