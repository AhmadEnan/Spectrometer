"""
Video capture manager for live spectrum mode.

Handles connection to various video sources (webcam, network stream, etc.)
with threading for smooth capture.
"""

import cv2
import numpy as np
from typing import Optional, Union, Tuple
import threading
import time
import logging
from queue import Queue

from utils.error_handler import VideoConnectionError

logger = logging.getLogger(__name__)


class VideoManager:
    """Manage video capture from multiple sources."""
    
    def __init__(self):
        """Initialize video manager."""
        self.cap: Optional[cv2.VideoCapture] = None
        self.source: Optional[Union[int, str]] = None
        self.is_running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_queue: Queue = Queue(maxsize=2)
        self._lock = threading.Lock()
        
        # Stats
        self.fps = 0.0
        self.frame_count = 0
        self.drop_count = 0
        self._last_fps_update = 0
        self._last_frame_count = 0
    
    def connect(self, source: Union[int, str] = 0) -> bool:
        """
        Connect to a video source.
        
        Args:
            source: Video source:
                   - int: Camera index (0, 1, 2, ...)
                   - str: URL (RTSP, HTTP, etc.) or video file path
                   
        Returns:
            True if connected successfully
            
        Raises:
            VideoConnectionError: If connection fails
        """
        # Disconnect existing
        if self.is_connected():
            self.disconnect()
        
        logger.info(f"Connecting to video source: {source}")
        
        # Open capture
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            raise VideoConnectionError(str(source))
        
        self.source = source
        
        # Get properties
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Connected: {width}x{height} @ {fps:.1f}fps")
        
        # Start capture thread
        self.is_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        
        return True
    
    def disconnect(self) -> None:
        """Disconnect from video source."""
        logger.info("Disconnecting video source")
        
        # Stop thread
        self.is_running = False
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
        
        # Release capture
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        # Clear queue
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except:
                break
        
        self.source = None
        self.frame_count = 0
        self.drop_count = 0
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        Read the latest frame.
        
        Returns:
            Latest frame or None if not available
        """
        if not self.is_connected():
            return None
        
        # Get latest frame from queue (non-blocking)
        frame = None
        try:
            while not self._frame_queue.empty():
                frame = self._frame_queue.get_nowait()
        except:
            pass
        
        return frame
    
    def is_connected(self) -> bool:
        """Check if video source is connected."""
        return self.cap is not None and self.is_running
    
    def get_properties(self) -> dict:
        """
        Get video source properties.
        
        Returns:
            Dictionary of properties
        """
        if not self.is_connected():
            return {}
        
        return {
            'width': int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.fps,
            'source': str(self.source),
            'frame_count': self.frame_count,
            'drop_count': self.drop_count
        }
    
    def set_resolution(self, width: int, height: int) -> bool:
        """
        Set capture resolution (may not be supported by all sources).
        
        Args:
            width: Target width
            height: Target height
            
        Returns:
            True if successful
        """
        if not self.is_connected():
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Verify
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        success = (actual_width == width and actual_height == height)
        
        if success:
            logger.info(f"Set resolution to {width}x{height}")
        else:
            logger.warning(
                f"Failed to set resolution to {width}x{height}, "
                f"got {actual_width}x{actual_height}"
            )
        
        return success
    
    def _capture_loop(self) -> None:
        """
        Capture loop running in thread.
        
        Continuously reads frames and puts them in queue.
        """
        logger.info("Capture thread started")
        
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                # Update stats
                self.frame_count += 1
                
                # Put frame in queue (drop old if full)
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()  # Remove old frame
                        self.drop_count += 1
                    except:
                        pass
                
                self._frame_queue.put(frame)
                
                # Update FPS
                current_time = time.time()
                if current_time - self._last_fps_update >= 1.0:
                    frames_in_second = self.frame_count - self._last_frame_count
                    self.fps = frames_in_second / (current_time - self._last_fps_update)
                    self._last_fps_update = current_time
                    self._last_frame_count = self.frame_count
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
        
        logger.info("Capture thread stopped")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.disconnect()
