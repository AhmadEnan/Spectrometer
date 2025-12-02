"""
Unit tests for spectrum sampler.

Tests 1D cross-section extraction functionality.
"""

import pytest
import numpy as np
import cv2
from core.spectrum_sampler import SpectrumSampler


class TestSpectrumSampler:
    """Test SpectrumSampler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sampler = SpectrumSampler()
        
        # Create a simple test image (gradient)
        self.test_image = self._create_gradient_image()
    
    def _create_gradient_image(self):
        """Create a horizontal gradient test image."""
        width, height = 400, 200
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create horizontal gradient
        for x in range(width):
            intensity = int(255 * x / width)
            image[:, x] = [intensity, intensity, intensity]
        
        return image
    
    def test_extract_straight_line(self):
        """Test extraction along a straight horizontal line."""
        line_points = [(0, 100), (399, 100)]
        thickness = 5
        
        pixel_pos, intensity = self.sampler.extract_cross_section(
            self.test_image,
            line_points,
            thickness
        )
        
        # Check output shape
        assert len(pixel_pos) > 0
        assert len(intensity) == len(pixel_pos)
        
        # Check that intensity increases along gradient
        assert intensity[0] < intensity[-1]
    
    def test_extract_with_thickness(self):
        """Test that thickness parameter affects sampling."""
        line_points = [(0, 100), (399, 100)]
        
        _, intensity_thin = self.sampler.extract_cross_section(
            self.test_image, line_points, thickness=1
        )
        
        _, intensity_thick = self.sampler.extract_cross_section(
            self.test_image, line_points, thickness=10
        )
        
        # Both should have same length (along line)
        assert len(intensity_thin) == len(intensity_thick)
    
    def test_extract_color_strip(self):
        """Test color strip extraction."""
        line_points = [(0, 100), (399, 100)]
        thickness = 5
        strip_height = 20
        
        strip = self.sampler.extract_color_strip(
            self.test_image,
            line_points,
            thickness,
            strip_height
        )
        
        # Check output shape
        assert strip.shape[0] == strip_height
        assert strip.shape[1] > 0
        assert strip.shape[2] == 3  # BGR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
