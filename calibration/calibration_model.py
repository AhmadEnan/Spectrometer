"""
Calibration model for pixel-to-wavelength mapping.

Uses polynomial fitting to map pixel positions to wavelength values.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CalibrationPoint:
    """A single calibration point."""
    
    pixel: float  # Pixel position
    wavelength: float  # Wavelength in nm
    label: Optional[str] = None  # Optional label (e.g., "532nm laser")


class CalibrationModel:
    """Pixel-to-wavelength calibration model."""
    
    def __init__(self, polynomial_order: int = 2):
        """
        Initialize calibration model.
        
        Args:
            polynomial_order: Order of polynomial (1=linear, 2=quadratic, 3=cubic)
        """
        self.polynomial_order = polynomial_order
        self.points: List[CalibrationPoint] = []
        self.coefficients: Optional[np.ndarray] = None
        self._fit_quality: Optional[Dict[str, float]] = None
    
    def add_point(
        self,
        pixel: float,
        wavelength: float,
        label: Optional[str] = None
    ) -> None:
        """
        Add a calibration point.
        
        Args:
            pixel: Pixel position
            wavelength: Wavelength in nm
            label: Optional label for this point
        """
        point = CalibrationPoint(pixel, wavelength, label)
        self.points.append(point)
        logger.info(f"Added calibration point: pixel={pixel:.1f}, λ={wavelength}nm")
        
        # Invalidate fit
        self.coefficients = None
        self._fit_quality = None
    
    def remove_point(self, index: int) -> None:
        """
        Remove a calibration point by index.
        
        Args:
            index: Index of point to remove
        """
        if 0 <= index < len(self.points):
            removed = self.points.pop(index)
            logger.info(f"Removed calibration point: {removed}")
            
            # Invalidate fit
            self.coefficients = None
            self._fit_quality = None
    
    def clear_points(self) -> None:
        """Clear all calibration points."""
        self.points.clear()
        self.coefficients = None
        self._fit_quality = None
        logger.info("Cleared all calibration points")
    
    def fit(self, order: Optional[int] = None) -> bool:
        """
        Fit polynomial to calibration points.
        
        Args:
            order: Polynomial order (None = use default)
            
        Returns:
            True if fit successful, False otherwise
        """
        if len(self.points) < 2:
            logger.warning("Need at least 2 calibration points to fit")
            return False
        
        if order is not None:
            self.polynomial_order = order
        
        # Need at least order+1 points
        if len(self.points) < self.polynomial_order + 1:
            logger.warning(
                f"Need at least {self.polynomial_order + 1} points "
                f"for order {self.polynomial_order} polynomial"
            )
            # Try lower order
            self.polynomial_order = min(self.polynomial_order, len(self.points) - 1)
        
        # Extract data
        pixels = np.array([p.pixel for p in self.points])
        wavelengths = np.array([p.wavelength for p in self.points])
        
        # Fit polynomial
        self.coefficients = np.polyfit(pixels, wavelengths, self.polynomial_order)
        
        # Calculate fit quality
        self._calculate_fit_quality(pixels, wavelengths)
        
        logger.info(
            f"Fitted polynomial (order {self.polynomial_order}): "
            f"R²={self._fit_quality['r_squared']:.4f}"
        )
        
        return True
    
    def pixel_to_wavelength(self, pixels: np.ndarray) -> np.ndarray:
        """
        Convert pixel positions to wavelengths.
        
        Args:
            pixels: Array of pixel positions
            
        Returns:
            Array of wavelengths in nm
            
        Raises:
            ValueError: If model is not fitted
        """
        if self.coefficients is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        wavelengths = np.polyval(self.coefficients, pixels)
        
        return wavelengths
    
    def wavelength_to_pixel(self, wavelength: float, method: str = 'newton') -> float:
        """
        Convert wavelength to pixel position (inverse mapping).
        
        Note: This is an approximate inverse.
        
        Args:
            wavelength: Wavelength in nm
            method: Inverse method ('newton' or 'bisect')
            
        Returns:
            Approximate pixel position
        """
        if self.coefficients is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        # For linear case, we can solve analytically
        if self.polynomial_order == 1:
            # λ = a*x + b → x = (λ - b) / a
            a, b = self.coefficients
            return (wavelength - b) / a
        
        # For higher orders, use numerical methods
        from scipy.optimize import fsolve
        
        # Objective function
        def objective(x):
            return np.polyval(self.coefficients, x) - wavelength
        
        # Initial guess (midpoint of calibration range)
        pixels = [p.pixel for p in self.points]
        x0 = (min(pixels) + max(pixels)) / 2
        
        # Solve
        result = fsolve(objective, x0)[0]
        
        return result
    
    def get_fit_quality(self) -> Optional[Dict[str, float]]:
        """
        Get fit quality metrics.
        
        Returns:
            Dictionary with R², RMSE, max error, etc., or None if not fitted
        """
        return self._fit_quality
    
    def _calculate_fit_quality(self, pixels: np.ndarray, wavelengths: np.ndarray) -> None:
        """
        Calculate fit quality metrics.
        
        Args:
            pixels: Pixel positions
            wavelengths: True wavelengths
        """
        # Predicted wavelengths
        pred_wavelengths = np.polyval(self.coefficients, pixels)
        
        # Residuals
        residuals = wavelengths - pred_wavelengths
        
        # R² (coefficient of determination)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((wavelengths - np.mean(wavelengths))**2)
        r_squared = 1 - (ss_res / (ss_tot + 1e-10))
        
        # RMSE
        rmse = np.sqrt(np.mean(residuals**2))
        
        # Max error
        max_error = np.max(np.abs(residuals))
        
        self._fit_quality = {
            'r_squared': r_squared,
            'rmse': rmse,
            'max_error': max_error,
            'residuals': residuals.tolist()
        }
    
    def is_fitted(self) -> bool:
        """Check if model is fitted."""
        return self.coefficients is not None
    
    def get_wavelength_range(self) -> Optional[Tuple[float, float]]:
        """
        Get the wavelength range covered by calibration.
        
        Returns:
            Tuple of (min_wavelength, max_wavelength) or None if not fitted
        """
        if not self.points:
            return None
        
        wavelengths = [p.wavelength for p in self.points]
        return (min(wavelengths), max(wavelengths))
    
    def get_pixel_range(self) -> Optional[Tuple[float, float]]:
        """
        Get the pixel range covered by calibration.
        
        Returns:
            Tuple of (min_pixel, max_pixel) or None if not fitted
        """
        if not self.points:
            return None
        
        pixels = [p.pixel for p in self.points]
        return (min(pixels), max(pixels))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize model to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'polynomial_order': self.polynomial_order,
            'points': [asdict(p) for p in self.points],
            'coefficients': self.coefficients.tolist() if self.coefficients is not None else None,
            'fit_quality': self._fit_quality
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationModel':
        """
        Deserialize model from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            CalibrationModel instance
        """
        model = cls(polynomial_order=data['polynomial_order'])
        
        # Restore points
        for p_data in data['points']:
            model.points.append(CalibrationPoint(**p_data))
        
        # Restore coefficients
        if data['coefficients'] is not None:
            model.coefficients = np.array(data['coefficients'])
        
        # Restore fit quality
        model._fit_quality = data['fit_quality']
        
        return model
