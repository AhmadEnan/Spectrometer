"""
Color space conversion utilities.

CRITICAL: All conversions preserve color integrity and avoid saturation changes.
Linear RGB is used for intensity calculations to maintain physical accuracy.
"""

import numpy as np
from typing import Union


def srgb_to_linear(value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Convert sRGB value(s) to linear RGB using proper gamma correction.
    
    Args:
        value: sRGB value(s) in range [0, 1]
        
    Returns:
        Linear RGB value(s)
    """
    # sRGB to linear conversion
    # https://en.wikipedia.org/wiki/SRGB#Specification_of_the_transformation
    if isinstance(value, np.ndarray):
        linear = np.where(
            value <= 0.04045,
            value / 12.92,
            np.power((value + 0.055) / 1.055, 2.4)
        )
        return linear
    else:
        if value <= 0.04045:
            return value / 12.92
        else:
            return ((value + 0.055) / 1.055) ** 2.4


def linear_to_srgb(value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Convert linear RGB value(s) to sRGB using proper gamma correction.
    
    Args:
        value: Linear RGB value(s)
        
    Returns:
        sRGB value(s) in range [0, 1]
    """
    if isinstance(value, np.ndarray):
        srgb = np.where(
            value <= 0.0031308,
            value * 12.92,
            1.055 * np.power(value, 1.0 / 2.4) - 0.055
        )
        return srgb
    else:
        if value <= 0.0031308:
            return value * 12.92
        else:
            return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def bgr_to_linear_rgb(image: np.ndarray) -> np.ndarray:
    """
    Convert BGR image (OpenCV format) to linear RGB.
    
    CRITICAL: This preserves color integrity by applying proper gamma correction.
    Do NOT use for saturation-modifying operations.
    
    Args:
        image: BGR image, uint8 [0, 255] or float [0, 1]
        
    Returns:
        Linear RGB image as float [0, 1]
    """
    # Convert to float if needed
    if image.dtype == np.uint8:
        image = image.astype(np.float32) / 255.0
    
    # BGR to RGB
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
    
    # sRGB to linear
    linear_rgb = srgb_to_linear(rgb)
    
    return linear_rgb


def rgb_to_intensity(image: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to intensity (luminance) using proper photometric weights.
    
    Uses ITU-R BT.709 standard for luminance calculation.
    Input should be in linear RGB color space for physical accuracy.
    
    Args:
        image: RGB image in linear color space, shape (H, W, 3)
        
    Returns:
        Intensity image, shape (H, W)
    """
    # ITU-R BT.709 coefficients for luminance
    # These are for linear RGB, not sRGB!
    weights = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    
    if len(image.shape) == 2:
        # Already grayscale
        return image
    
    # Weighted sum
    intensity = np.dot(image, weights)
    
    return intensity


def bgr_to_intensity(image: np.ndarray) -> np.ndarray:
    """
    Convert BGR image directly to intensity.
    
    Convenience function that combines bgr_to_linear_rgb and rgb_to_intensity.
    
    Args:
        image: BGR image (OpenCV format)
        
    Returns:
        Intensity image
    """
    linear_rgb = bgr_to_linear_rgb(image)
    intensity = rgb_to_intensity(linear_rgb)
    return intensity


# Import cv2 (needed for color conversion)
try:
    import cv2
except ImportError:
    # Provide fallback without cv2 (though it's required in requirements.txt)
    def bgr_to_linear_rgb(image: np.ndarray) -> np.ndarray:
        """Fallback without cv2."""
        if image.dtype == np.uint8:
            image = image.astype(np.float32) / 255.0
        
        # Assume BGR, flip to RGB
        if len(image.shape) == 3:
            rgb = image[..., ::-1]
        else:
            rgb = image
            
        return srgb_to_linear(rgb)
