"""
Spectrum graph widget with embedded matplotlib.

Displays intensity vs wavelength/pixel with spectrum strip overlay.
CRITICAL: Strip and graph must share horizontal alignment.
"""

import numpy as np
from typing import Optional, Tuple
import logging

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Signal, Qt


from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.gridspec import GridSpec
from scipy.signal import savgol_filter

logger = logging.getLogger(__name__)


class SpectrumGraph(QWidget):
    """Spectrum graph widget with strip overlay."""
    
    # Signals
    position_hovered = Signal(float)  # Emits x-position when mouse hovers
    point_clicked = Signal(float)  # Emits x-position when clicked (interactive mode)
    
    def __init__(self, parent=None):
        """Initialize spectrum graph widget."""
        super().__init__(parent)
        
        # Data
        self.pixel_positions: Optional[np.ndarray] = None
        self.intensity: Optional[np.ndarray] = None
        self.wavelengths: Optional[np.ndarray] = None
        self.spectrum_strip: Optional[np.ndarray] = None
        
        # Settings
        self.show_smoothed = True
        self.scale_type = 'linear'  # 'linear' or 'log'
        self.savgol_window = 11
        self.savgol_order = 3
        
        # Interactive calibration mode
        self.interactive_mode = False
        self.calibration_markers = []  # List of (x_pos, wavelength, label)
        
        # Create matplotlib figure with constrained_layout
        self.figure = Figure(figsize=(8, 4), facecolor='#2b2b2b', constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setStyleSheet("background-color: #2b2b2b;")
        
        # Add navigation toolbar (hidden by default, or visible?)
        # Let's make it visible but compact, or just standard
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #333; color: white;")
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Create subplots
        self._setup_plots()
        
        # Mouse interaction
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self._on_mouse_click)
        
        self._cursor_line = None
        self._marker_lines = []  # Visual marker lines
        self._marker_texts = []  # Visual marker labels
    
    def _setup_plots(self) -> None:
        """Set up matplotlib subplots."""
        self.figure.clear()
        
        # Create grid: strip on top, graph below
        gs = GridSpec(2, 1, figure=self.figure, height_ratios=[1, 4], hspace=0.05)
        
        # Strip axes (top)
        self.strip_ax = self.figure.add_subplot(gs[0])
        self.strip_ax.set_facecolor('#1a1a1a')
        self.strip_ax.set_xticks([])
        self.strip_ax.set_yticks([])
        
        # Graph axes (bottom)
        self.graph_ax = self.figure.add_subplot(gs[1])
        self.graph_ax.set_facecolor('#1a1a1a')
        self.graph_ax.tick_params(colors='white')
        self.graph_ax.spines['bottom'].set_color('white')
        self.graph_ax.spines['left'].set_color('white')
        self.graph_ax.spines['top'].set_visible(False)
        self.graph_ax.spines['right'].set_visible(False)
        
        # Labels
        self.graph_ax.set_xlabel('Wavelength (nm)', color='white')
        self.graph_ax.set_ylabel('Intensity', color='white')
        
        

    
    def set_data(
        self,
        pixel_positions: np.ndarray,
        intensity: np.ndarray,
        wavelengths: Optional[np.ndarray] = None,
        spectrum_strip: Optional[np.ndarray] = None
    ) -> None:
        """
        Set spectrum data.
        
        Args:
            pixel_positions: X positions(pixels)
            intensity: Intensity values
            wavelengths: Optional wavelength values (calibrated)
            spectrum_strip: Optional color strip image (H x W x 3)
        """
        self.pixel_positions = pixel_positions
        self.intensity = intensity
        self.wavelengths = wavelengths
        self.spectrum_strip = spectrum_strip
        
        self.plot()
    
    def plot(self) -> None:
        """Plot the spectrum."""
        if self.pixel_positions is None or self.intensity is None:
            return
        
        # Clear axes
        self.strip_ax.clear()
        self.graph_ax.clear()
        
        # Plot spectrum strip if available
        if self.spectrum_strip is not None:
            # Display strip (origin='upper' to match typical image orientation)
            self.strip_ax.imshow(
                self.spectrum_strip,
                aspect='auto',
                extent=[self.pixel_positions[0], self.pixel_positions[-1], 0, 1],
                origin='upper'
            )
        
        self.strip_ax.set_xlim(self.pixel_positions[0], self.pixel_positions[-1])
        self.strip_ax.set_xticks([])
        self.strip_ax.set_yticks([])
        
        # Determine x-axis (pixels or wavelengths)
        if self.wavelengths is not None:
            x_data = self.wavelengths
            xlabel = 'Pixel position'
        else:
            x_data = self.pixel_positions
            xlabel = 'Wavelength (nm)'
        
        # Plot raw intensity
        self.graph_ax.plot(
            x_data, self.intensity,
            color='#888888', linewidth=0.5, alpha=0.5, label='Raw'
        )
        
        # Plot smoothed intensity if enabled
        if self.show_smoothed and len(self.intensity) > self.savgol_window:
            try:
                smoothed = savgol_filter(
                    self.intensity,
                    self.savgol_window,
                    min(self.savgol_order, self.savgol_window - 1)
                )
                self.graph_ax.plot(
                    x_data, smoothed,
                    color='#0d7377', linewidth=2, label='Smoothed'
                )
            except Exception as e:
                logger.warning(f"Failed to apply Savitzky-Golay filter: {e}")
        
        # Set scale
        if self.scale_type == 'log':
            self.graph_ax.set_yscale('log')
        else:
            self.graph_ax.set_yscale('linear')
        
        # Labels
        self.graph_ax.set_xlabel(xlabel, color='white')
        self.graph_ax.set_ylabel('Intensity', color='white')
        
        # Style
        self.graph_ax.tick_params(colors='white')
        self.graph_ax.spines['bottom'].set_color('white')
        self.graph_ax.spines['left'].set_color('white')
        self.graph_ax.spines['top'].set_visible(False)
        self.graph_ax.spines['right'].set_visible(False)
        self.graph_ax.set_facecolor('#1a1a1a')
        
        # Legend
        if self.show_smoothed:
            self.graph_ax.legend(facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        
        # Grid
        self.graph_ax.grid(True, alpha=0.2, color='white')
        

        
        # Draw calibration markers
        self._draw_calibration_markers()
        
        self.canvas.draw()
    
    def _on_mouse_move(self, event) -> None:
        """Handle mouse move event."""
        if event.inaxes in [self.graph_ax, self.strip_ax] and event.xdata is not None:
            # Draw cursor line
            if self._cursor_line is not None:
                self._cursor_line.set_visible(False)
            
            self._cursor_line = self.graph_ax.axvline(
                event.xdata, color='yellow', linewidth=1, alpha=0.7
            )
            
            self.canvas.draw_idle()
            
            # Emit signal
            self.position_hovered.emit(event.xdata)
    
    def set_scale(self, scale_type: str) -> None:
        """
        Set Y-axis scale.
        
        Args:
            scale_type: 'linear' or 'log'
        """
        self.scale_type = scale_type
        self.plot()
    
    def set_show_smoothed(self, show: bool) -> None:
        """
        Toggle smoothed curve display.
        
        Args:
            show: Whether to show smoothed curve
        """
        self.show_smoothed = show
        self.plot()
    
    def set_smoothing_params(self, window: int, order: int) -> None:
        """
        Set Savitzky-Golay smoothing parameters.
        
        Args:
            window: Window size (must be odd)
            order: Polynomial order
        """
        if window % 2 == 0:
            window += 1
        self.savgol_window = max(3, window)
        self.savgol_order = min(order, window - 1)
        
        if self.show_smoothed:
            self.plot()
    
    def clear(self) -> None:
        """Clear the graph."""
        self.pixel_positions = None
        self.intensity = None
        self.wavelengths = None
        self.spectrum_strip = None
        
        self.strip_ax.clear()
        self.graph_ax.clear()
        self.canvas.draw()
    
    def _on_mouse_click(self, event) -> None:
        """Handle mouse click event."""
        if not self.interactive_mode:
            return
        
        if event.inaxes == self.graph_ax and event.xdata is not None:
            # Emit signal for click on graph
            self.point_clicked.emit(event.xdata)
    
    def set_interactive_mode(self, enabled: bool) -> None:
        """
        Enable/disable interactive calibration mode.
        
        Args:
            enabled: True to enable click-to-calibrate, False to disable
        """
        self.interactive_mode = enabled
        
        # Change cursor style
        if enabled:
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
        
        logger.info(f"Interactive calibration mode: {'enabled' if enabled else 'disabled'}")
    
    def add_calibration_marker(
        self,
        x_pos: float,
        wavelength: float,
        label: str = ""
    ) -> None:
        """
        Add a calibration marker at specified position.
        
        Args:
            x_pos: X position (pixel or wavelength)
            wavelength: Wavelength value in nm
            label: Optional label for the marker
        """
        self.calibration_markers.append((x_pos, wavelength, label))
        logger.info(f"Added calibration marker at x={x_pos:.2f}, λ={wavelength}nm")
        
        # Redraw if we have data
        if self.pixel_positions is not None:
            self.plot()
    
    def set_calibration_markers(
        self,
        markers: list[tuple[float, float, str]]
    ) -> None:
        """
        Set all calibration markers at once.
        
        Args:
            markers: List of (x_pos, wavelength, label) tuples
        """
        self.calibration_markers = markers
        logger.info(f"Set {len(markers)} calibration markers")
        
        if self.pixel_positions is not None:
            self.plot()
    
    def remove_calibration_marker(self, index: int) -> None:
        """
        Remove a calibration marker by index.
        
        Args:
            index: Index of marker to remove
        """
        if 0 <= index < len(self.calibration_markers):
            removed = self.calibration_markers.pop(index)
            logger.info(f"Removed calibration marker: {removed}")
            
            if self.pixel_positions is not None:
                self.plot()
    
    def clear_calibration_markers(self) -> None:
        """Clear all calibration markers."""
        self.calibration_markers.clear()
        logger.info("Cleared all calibration markers")
        
        if self.pixel_positions is not None:
            self.plot()
    
    def _draw_calibration_markers(self) -> None:
        """Draw calibration markers on the graph."""
        # Clear old marker visuals by setting visibility to False
        for line in self._marker_lines:
            line.set_visible(False)
        for text in self._marker_texts:
            text.set_visible(False)
        
        self._marker_lines.clear()
        self._marker_texts.clear()
        
        # Draw new markers
        for x_pos, wavelength, label in self.calibration_markers:
            # Vertical line
            line = self.graph_ax.axvline(
                x_pos,
                color='cyan',
                linewidth=2,
                linestyle='--',
                alpha=0.8
            )
            self._marker_lines.append(line)
            
            # Label text
            display_label = f"{wavelength:.1f}nm"
            if label:
                display_label = f"{label}\n{wavelength:.1f}nm"
            
            text = self.graph_ax.text(
                x_pos,
                self.graph_ax.get_ylim()[1] * 0.95,
                display_label,
                color='cyan',
                fontsize=9,
                ha='center',
                va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#2b2b2b', edgecolor='cyan', alpha=0.8)
            )
            self._marker_texts.append(text)
