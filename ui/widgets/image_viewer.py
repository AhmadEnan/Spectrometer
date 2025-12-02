"""
Interactive image viewer widget for spectrum images.

Displays spectrum image with zoom, pan, and overlay for line selection.
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple
import logging

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

logger = logging.getLogger(__name__)


class ImageViewer(QWidget):
    """Interactive image display widget."""
    
    # Signals
    line_drawn = Signal(list)  # Emits list of (x, y) points
    mouse_moved = Signal(int, int)  # Emits (x, y) position
    
    def __init__(self, parent=None):
        """Initialize image viewer."""
        super().__init__(parent)
        
        # Image data
        self.image: Optional[np.ndarray] = None
        self.display_pixmap: Optional[QPixmap] = None
        
        # Line overlay
        self.line_points: List[Tuple[int, int]] = []
        self.thickness: int = 5
        
        # Drawing state
        self.is_drawing = False
        self.draw_start: Optional[Tuple[int, int]] = None
        self.draw_end: Optional[Tuple[int, int]] = None
        
        # UI
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1a1a1a;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setMinimumSize(1, 1)  # Prevent layout expansion loop

        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        
        # Mouse tracking and events
        self.setMouseTracking(True)
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Filter mouse events on image label."""
        if obj == self.image_label and self.image is not None:
            if event.type() == event.Type.MouseButtonPress:
                self._on_mouse_press(event)
                return True
            elif event.type() == event.Type.MouseMove:
                self._on_mouse_move(event)
                return True
            elif event.type() == event.Type.MouseButtonRelease:
                self._on_mouse_release(event)
                return True
        return super().eventFilter(obj, event)
    
    def _on_mouse_press(self, event) -> None:
        """Handle mouse press to start drawing."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert widget coordinates to image coordinates
            pos = self._widget_to_image_coords(event.pos())
            if pos:
                self.is_drawing = True
                self.draw_start = pos
                self.draw_end = pos
                self._update_display()
    
    def _on_mouse_move(self, event) -> None:
        """Handle mouse move while drawing."""
        if self.is_drawing:
            pos = self._widget_to_image_coords(event.pos())
            if pos:
                self.draw_end = pos
                self._update_display()
    
    def _on_mouse_release(self, event) -> None:
        """Handle mouse release to finish drawing."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            pos = self._widget_to_image_coords(event.pos())
            if pos:
                self.draw_end = pos
                self.is_drawing = False
                
                # Set the line
                self.line_points = [self.draw_start, self.draw_end]
                self.line_drawn.emit(self.line_points)
                
                # Clear drawing state
                self.draw_start = None
                self.draw_end = None
                
                self._update_display()
                logger.info(f"Line drawn: {self.line_points}")
    
    def _widget_to_image_coords(self, pos: QPoint) -> Optional[Tuple[int, int]]:
        """Convert widget coordinates to image coordinates."""
        if self.image is None or self.display_pixmap is None:
            return None
        
        # Get pixmap rect (centered in label)
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return None
            
        pixmap_rect = pixmap.rect()
        label_rect = self.image_label.rect()
        
        # Calculate offset (pixmap is centered)
        x_offset = (label_rect.width() - pixmap_rect.width()) // 2
        y_offset = (label_rect.height() - pixmap_rect.height()) // 2
        
        # Adjust position
        x = pos.x() - x_offset
        y = pos.y() - y_offset
        
        # Check if within pixmap bounds
        if x < 0 or y < 0 or x >= pixmap_rect.width() or y >= pixmap_rect.height():
            return None
        
        # Scale to original image coordinates
        scale_x = self.image.shape[1] / pixmap_rect.width()
        scale_y = self.image.shape[0] / pixmap_rect.height()
        
        img_x = int(x * scale_x)
        img_y = int(y * scale_y)
        
        # Clamp to image bounds
        img_x = max(0, min(img_x, self.image.shape[1] - 1))
        img_y = max(0, min(img_y, self.image.shape[0] - 1))
        
        return (img_x, img_y)
    
    def set_image(self, image: np.ndarray) -> None:
        """
        Set the image to display.
        
        Args:
            image: BGR image (OpenCV format)
        """
        self.image = image.copy()
        self._update_display()
    
    def set_line(self, line_points: List[Tuple[int, int]], thickness: int = 5) -> None:
        """
        Set the line overlay.
        
        Args:
            line_points: List of (x, y) points defining the line
            thickness: Line thickness for display
        """
        self.line_points = line_points
        self.thickness = thickness
        self._update_display()
    
    def clear_line(self) -> None:
        """Clear the line overlay."""
        self.line_points = []
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the displayed image with overlays."""
        if self.image is None:
            return
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        
        # Draw line overlay if present OR if currently drawing
        display_image = rgb_image.copy()
        
        # Draw completed line
        if len(self.line_points) >= 2:
            if len(self.line_points) == 2:
                # Straight line
                cv2.line(
                    display_image,
                    self.line_points[0],
                    self.line_points[1],
                    (13, 115, 119),  # Teal color
                    2
                )
                
                # Draw thickness preview
                x1, y1 = self.line_points[0]
                x2, y2 = self.line_points[1]
                dx = x2 - x1
                dy = y2 - y1
                length = np.sqrt(dx**2 + dy**2)
                if length > 0:
                    perp_x = -dy / length * self.thickness / 2
                    perp_y = dx / length * self.thickness / 2
                    
                    # Draw thickness lines
                    p1_top = (int(x1 + perp_x), int(y1 + perp_y))
                    p2_top = (int(x2 + perp_x), int(y2 + perp_y))
                    p1_bot = (int(x1 - perp_x), int(y1 - perp_y))
                    p2_bot = (int(x2 - perp_x), int(y2 - perp_y))
                    
                    cv2.line(display_image, p1_top, p2_top, (13, 115, 119), 1)
                    cv2.line(display_image, p1_bot, p2_bot, (13, 115, 119), 1)
            else:
                # Polyline
                for i in range(len(self.line_points) - 1):
                    cv2.line(
                        display_image,
                        self.line_points[i],
                        self.line_points[i + 1],
                        (13, 115, 119),
                        2
                    )
            
            # Draw points
            for point in self.line_points:
                cv2.circle(display_image, point, 5, (255, 200, 0), -1)
        
        # Draw temporary line while dragging
        if self.is_drawing and self.draw_start and self.draw_end:
            cv2.line(
                display_image,
                self.draw_start,
                self.draw_end,
                (255, 200, 0),  # Yellow while drawing
                2
            )
            # Draw endpoints
            cv2.circle(display_image, self.draw_start, 5, (255, 200, 0), -1)
            cv2.circle(display_image, self.draw_end, 5, (255, 200, 0), -1)
        
        # Convert to QPixmap
        height, width, channel = display_image.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            display_image.data,
            width, height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        
        self.display_pixmap = QPixmap.fromImage(q_image)
        
        # Scale to fit widget while maintaining aspect ratio
        scaled_pixmap = self.display_pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event) -> None:
        """Handle resize event."""
        super().resizeEvent(event)
        if self.display_pixmap is not None:
            self._update_display()
    
    def clear(self) -> None:
        """Clear the viewer."""
        self.image = None
        self.display_pixmap = None
        self.line_points = []
        self.image_label.clear()
