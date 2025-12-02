"""
Error handling framework for the spectrum analyzer.

Provides custom exception classes and user-friendly error handling.
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SpectrumError(Exception):
    """Base exception for spectrum analyzer errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or message


class NoSpectrumDetectedError(SpectrumError):
    """Raised when no spectrum line can be detected in the image."""
    
    def __init__(self, message: str = "No spectrum line detected in the image"):
        user_msg = (
            "Could not detect a spectrum line in the image. "
            "Please try:\n"
            "• Use manual line selection mode\n"
            "• Ensure the spectrum is clearly visible\n"
            "• Check image brightness and contrast"
        )
        super().__init__(message, user_msg)


class CalibrationError(SpectrumError):
    """Raised when calibration fails or is invalid."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        if user_message is None:
            user_message = (
                "Calibration error. Please ensure:\n"
                "• At least 2 calibration points are provided\n"
                "• Wavelength values are reasonable (200-1000 nm)\n"
                "• Peak positions are distinct"
            )
        super().__init__(message, user_message)


class VideoConnectionError(SpectrumError):
    """Raised when video capture connection fails."""
    
    def __init__(self, source: str):
        message = f"Failed to connect to video source: {source}"
        user_msg = (
            f"Could not connect to camera: {source}\n\n"
            "Troubleshooting:\n"
            "• Check if another app is using the camera\n"
            "• Verify the camera is properly connected\n"
            "• Try a different camera index (0, 1, 2...)\n"
            "• For network streams, check the URL and network connection"
        )
        super().__init__(message, user_msg)


class ImageLoadError(SpectrumError):
    """Raised when image loading fails."""
    
    def __init__(self, filepath: str):
        message = f"Failed to load image: {filepath}"
        user_msg = (
            f"Could not load image file.\n\n"
            "Please ensure:\n"
            "• The file exists and is accessible\n"
            "• The file is a valid image (PNG, JPG, WebP)\n"
            "• The file is not corrupted"
        )
        super().__init__(message, user_msg)


def handle_error(error: Exception, logger_obj: Optional[logging.Logger] = None) -> str:
    """
    Handle an exception and return a user-friendly message.
    
    Args:
        error: The exception that occurred
        logger_obj: Optional logger to use for logging the error
        
    Returns:
        User-friendly error message
    """
    log = logger_obj or logger
    
    if isinstance(error, SpectrumError):
        log.warning(f"{error.__class__.__name__}: {error}")
        return error.user_message
    else:
        log.error(f"Unexpected error: {error}", exc_info=True)
        return (
            f"An unexpected error occurred: {str(error)}\n\n"
            "Please check the logs for more details."
        )
