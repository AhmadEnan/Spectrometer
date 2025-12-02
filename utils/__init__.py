"""
Utility functions and helpers.
"""

from .error_handler import (
    SpectrumError,
    NoSpectrumDetectedError,
    CalibrationError,
    VideoConnectionError,
    ImageLoadError,
    handle_error
)
from .logger import setup_logger, get_logger
from .color_utils import (
    bgr_to_linear_rgb,
    rgb_to_intensity,
    linear_to_srgb,
    srgb_to_linear
)
from .config_manager import ConfigManager

__all__ = [
    'SpectrumError',
    'NoSpectrumDetectedError',
    'CalibrationError',
    'VideoConnectionError',
    'ImageLoadError',
    'handle_error',
    'setup_logger',
    'get_logger',
    'bgr_to_linear_rgb',
    'rgb_to_intensity',
    'linear_to_srgb',
    'srgb_to_linear',
    'ConfigManager'
]
