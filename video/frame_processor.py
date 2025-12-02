"""
Frame processor for live video mode.

Provides temporal smoothing and processing for video frames.
"""

import numpy as np
from typing import Optional, Deque
from collections import deque
import logging

logger = logging.getLogger(__name__)


class FrameProcessor:
    """Process video frames with temporal smoothing."""
    
    def __init__(self, smoothing_strength: float = 0.7, buffer_size: int = 5):
        """
        Initialize frame processor.
        
        Args:
            smoothing_strength: Exponential moving average weight [0, 1]
                              0 = no smoothing, 1 = maximum smoothing
            buffer_size: Number of frames to keep in history buffer
        """
        self.smoothing_strength = smoothing_strength
        self.buffer_size = buffer_size
        
        self._smoothed_frame: Optional[np.ndarray] = None
        self._frame_buffer: Deque[np.ndarray] = deque(maxlen=buffer_size)
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a video frame with temporal smoothing.
        
        Uses exponential moving average for smooth transitions.
        
        Args:
            frame: Input frame (BGR)
            
        Returns:
            Processed frame
        """
        # Convert to float for smoothing
        frame_float = frame.astype(np.float32)
        
        # Initialize smoothed frame on first call
        if self._smoothed_frame is None:
            self._smoothed_frame = frame_float.copy()
        
        # Apply exponential moving average
        alpha = 1.0 - self.smoothing_strength
        self._smoothed_frame = alpha * frame_float + self.smoothing_strength * self._smoothed_frame
        
        # Add to buffer
        self._frame_buffer.append(frame)
        
        # Convert back to uint8
        processed = np.clip(self._smoothed_frame, 0, 255).astype(np.uint8)
        
        return processed
    
    def get_averaged_frame(self, num_frames: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Get average of recent frames from buffer.
        
        Args:
            num_frames: Number of recent frames to average (None = all in buffer)
            
        Returns:
            Averaged frame or None if buffer empty
        """
        if len(self._frame_buffer) == 0:
            return None
        
        # Determine how many frames to use
        if num_frames is None or num_frames > len(self._frame_buffer):
            num_frames = len(self._frame_buffer)
        
        # Get recent frames
        recent_frames = list(self._frame_buffer)[-num_frames:]
        
        # Average
        averaged = np.mean(recent_frames, axis=0).astype(np.uint8)
        
        return averaged
    
    def reset(self) -> None:
        """Reset the processor state."""
        self._smoothed_frame = None
        self._frame_buffer.clear()
        logger.info("Frame processor reset")
    
    def set_smoothing_strength(self, strength: float) -> None:
        """
        Set smoothing strength.
        
        Args:
            strength: Smoothing strength [0, 1]
        """
        self.smoothing_strength = np.clip(strength, 0.0, 1.0)
        logger.debug(f"Set smoothing strength to {self.smoothing_strength:.2f}")
    
    def get_frame_variance(self) -> Optional[np.ndarray]:
        """
        Calculate variance across recent frames.
        
        Useful for detecting motion or changes.
        
        Returns:
            Variance image or None if not enough frames
        """
        if len(self._frame_buffer) < 2:
            return None
        
        frames = np.array(list(self._frame_buffer), dtype=np.float32)
        variance = np.var(frames, axis=0)
        
        return variance
