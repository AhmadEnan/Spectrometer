"""
Line selector widget for manual line drawing.

Allows user to draw line across spectrum image.
"""

from typing import Optional, List, Tuple
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QMouseEvent
import logging

logger = logging.getLogger(__name__)


class LineSelector(QWidget):
    """Widget for drawing lines on spectrum images."""
    
    # Signals
    line_updated = Signal(list)  # Emits list of (x, y) tuples
    
    def __init__(self, parent=None):
        """Initialize line selector."""
        super().__init__(parent)
        
        self.start_point: Optional[QPoint] = None
        self.end_point: Optional[QPoint] = None
        self.is_drawing = False
        
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # Make transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press - start drawing line."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_drawing = True
            self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move - update line endpoint."""
        if self.is_drawing:
            self.end_point = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release - finish drawing line."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.end_point = event.pos()
            self.is_drawing = False
            self.update()
            
            # Emit line
            if self.start_point and self.end_point:
                line_points = [
                    (self.start_point.x(), self.start_point.y()),
                    (self.end_point.x(), self.end_point.y())
                ]
                self.line_updated.emit(line_points)
                logger.info(f"Line drawn: {line_points}")
    
    def paintEvent(self, event) -> None:
        """Paint the line."""
        if self.start_point and self.end_point:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw line
            pen = QPen(QColor(13, 115, 119), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.start_point, self.end_point)
            
            # Draw endpoints
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 200, 0))
            painter.drawEllipse(self.start_point, 5, 5)
            painter.drawEllipse(self.end_point, 5, 5)
    
    def clear(self) -> None:
        """Clear the line."""
        self.start_point = None
        self.end_point = None
        self.is_drawing = False
        self.update()
