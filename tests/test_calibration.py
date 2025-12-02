"""
Unit tests for calibration model.

Tests polynomial fitting and wavelength mapping.
"""

import pytest
import numpy as np
from calibration.calibration_model import CalibrationModel, CalibrationPoint


class TestCalibrationModel:
    """Test CalibrationModel class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.model = CalibrationModel(polynomial_order=2)
    
    def test_add_point(self):
        """Test adding calibration points."""
        self.model.add_point(100, 405)  # 405nm laser at pixel 100
        self.model.add_point(300, 532)  # 532nm laser at pixel 300
        
        assert len(self.model.points) == 2
        assert self.model.points[0].pixel == 100
        assert self.model.points[0].wavelength == 405
    
    def test_linear_fit(self):
        """Test linear calibration fit."""
        # Create linear relationship: wavelength = 2 * pixel + 300
        self.model.add_point(50, 400)   # 2*50 + 300 = 400
        self.model.add_point(100, 500)  # 2*100 + 300 = 500
        
        # Fit with linear model
        success = self.model.fit(order=1)
        assert success
        assert self.model.is_fitted()
        
        # Test prediction
        wavelengths = self.model.pixel_to_wavelength(np.array([75]))
        assert np.isclose(wavelengths[0], 450, atol=1)  # 2*75 + 300 = 450
    
    def test_quadratic_fit(self):
        """Test quadratic calibration fit."""
        # Add points with quadratic relationship
        self.model.add_point(0, 400)
        self.model.add_point(100, 500)
        self.model.add_point(200, 650)
        
        success = self.model.fit(order=2)
        assert success
        
        # Check fit quality
        quality = self.model.get_fit_quality()
        assert quality['r_squared'] > 0.9  # Should be good fit
    
    def test_insufficient_points(self):
        """Test that fitting fails with insufficient points."""
        self.model.add_point(100, 500)
        
        success = self.model.fit()
        assert not success  # Should fail with only 1 point
    
    def test_clear_points(self):
        """Test clearing calibration points."""
        self.model.add_point(100, 500)
        self.model.add_point(200, 600)
        
        self.model.clear_points()
        assert len(self.model.points) == 0
        assert not self.model.is_fitted()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
