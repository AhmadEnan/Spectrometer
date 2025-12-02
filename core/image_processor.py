"""
Image preprocessing utilities for spectrum analysis.

Provides smoothing, background removal, and enhancement operations
while preserving color integrity.
"""

import cv2
import numpy as np
from scipy import ndimage
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image preprocessing for spectrum analysis."""
    
    @staticmethod
    def gaussian_blur(image: np.ndarray, kernel_size: int = 5, sigma: float = 0) -> np.ndarray:
        """
        Apply Gaussian blur to reduce noise.
        
        Args:
            image: Input image
            kernel_size: Kernel size (must be odd)
            sigma: Gaussian kernel standard deviation (0 = auto)
            
        Returns:
            Blurred image
        """
        if kernel_size % 2 == 0:
            kernel_size += 1  # Ensure odd
        
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
    
    @staticmethod
    def median_filter(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        Apply median filter to remove salt-and-pepper noise.
        
        Args:
            image: Input image
            kernel_size: Kernel size
            
        Returns:
            Filtered image
        """
        return cv2.medianBlur(image, kernel_size)
    
    @staticmethod
    def remove_background(
        image: np.ndarray,
        strength: float = 0.0,
        method: str = 'adaptive'
    ) -> np.ndarray:
        """
        Remove background noise without modifying saturation.
        
        CRITICAL: This does NOT alter color saturation, only removes dark noise.
        
        Args:
            image: Input image (BGR or grayscale)
            strength: Background removal strength [0, 1]
            method: 'adaptive' or 'morphological'
            
        Returns:
            Image with background removed
        """
        if strength <= 0:
            return image
        
        # Work with grayscale for background detection
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if method == 'adaptive':
            # Adaptive thresholding to find background
            block_size = int(gray.shape[1] * 0.1)
            if block_size % 2 == 0:
                block_size += 1
            block_size = max(3, min(block_size, 255))
            
            threshold = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size, 2
            )
            
            # Create mask (foreground = spectrum)
            mask = threshold.astype(np.float32) / 255.0
            
        else:  # morphological
            # Use morphological opening to estimate background
            kernel_size = int(gray.shape[1] * 0.05)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            
            # Subtract background
            diff = cv2.subtract(gray, background)
            
            # Normalize to create mask
            mask = cv2.normalize(diff, None, 0, 1, cv2.NORM_MINMAX).astype(np.float32)
        
        # Apply mask with strength
        mask = strength * mask + (1 - strength) * 1.0
        
        # Apply to image
        if len(image.shape) == 3:
            mask = mask[..., np.newaxis]
        
        result = (image.astype(np.float32) * mask).astype(image.dtype)
        
        return result
    
    @staticmethod
    def auto_contrast(image: np.ndarray, percentile: float = 2.0) -> np.ndarray:
        """
        Apply auto-contrast for display purposes only.
        
        WARNING: This should NEVER be used for analysis data.
        Only for display enhancement.
        
        Args:
            image: Input image
            percentile: Percentile for clipping (default 2%)
            
        Returns:
            Contrast-enhanced image
        """
        if image.dtype == np.uint8:
            # Find percentile values
            p_low = np.percentile(image, percentile)
            p_high = np.percentile(image, 100 - percentile)
            
            # Clip and rescale
            clipped = np.clip(image, p_low, p_high)
            result = ((clipped - p_low) / (p_high - p_low) * 255).astype(np.uint8)
            
            return result
        else:
            # Float image
            p_low = np.percentile(image, percentile)
            p_high = np.percentile(image, 100 - percentile)
            
            clipped = np.clip(image, p_low, p_high)
            result = (clipped - p_low) / (p_high - p_low)
            
            return result
    
    @staticmethod
    def enhance_edges(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Enhance edges for line detection.
        
        Args:
            image: Input image (grayscale)
            strength: Edge enhancement strength
            
        Returns:
            Edge-enhanced image
        """
        # Laplacian edge detection
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        
        # Add back to original with strength
        enhanced = image.astype(np.float64) + strength * laplacian
        
        # Clip and convert back
        enhanced = np.clip(enhanced, 0, 255).astype(image.dtype)
        
        return enhanced
    
    @staticmethod
    def bilateral_filter(
        image: np.ndarray,
        d: int = 9,
        sigma_color: float = 75,
        sigma_space: float = 75
    ) -> np.ndarray:
        """
        Apply bilateral filter (edge-preserving smoothing).
        
        Args:
            image: Input image
            d: Diameter of pixel neighborhood
            sigma_color: Color space sigma
            sigma_space: Coordinate space sigma
            
        Returns:
            Filtered image
        """
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
