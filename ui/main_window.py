"""
Main application window.

Tabbed interface with static analysis, live mode, and calibration.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QFileDialog, QMessageBox,
    QLabel, QSplitter, QStatusBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from .widgets import (
    ImageViewer, LineSelector, SpectrumGraph,
    InspectorPanel, CalibrationWidget
)
from core import SpectrumSampler, AutoLineDetector, ImageProcessor
from calibration import CalibrationModel
from video import VideoManager, FrameProcessor
from utils import (
    setup_logger, get_logger,
    ImageLoadError, NoSpectrumDetectedError,
    handle_error, ConfigManager
)

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        # Initialize components
        self.config = ConfigManager()
        self.spectrum_sampler = SpectrumSampler()
        self.line_detector = AutoLineDetector()
        self.image_processor = ImageProcessor()
        self.video_manager = VideoManager()
        self.frame_processor = FrameProcessor()
        self.calibration_model: Optional[CalibrationModel] = None
        
        # Current state
        self.current_image: Optional[np.ndarray] = None
        self.current_line_points: List[Tuple[int, int]] = []
        self.current_thickness = 5
        self.current_pixel_positions: Optional[np.ndarray] = None
        self.current_intensity: Optional[np.ndarray] = None
        self.rotation_angle = 0  # Track current rotation (0, 90, 180, 270)
        
        # Set up UI
        self.setWindowTitle("Spectrum Analyzer")
        self.setGeometry(100, 100, 1400, 800)
        
        self._create_menu_bar()
        self._create_ui()
        self._create_status_bar()
        
        # Timer for live video
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self._update_video_frame)
        
        logger.info("Application initialized")
    
    def _create_menu_bar(self) -> None:
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Image...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_image)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_ui(self) -> None:
        """Create main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Static Image Analysis
        static_tab = self._create_static_tab()
        self.tabs.addTab(static_tab, "Static Image Analysis")
        
        # Tab 2: Live Video Mode
        live_tab = self._create_live_tab()
        self.tabs.addTab(live_tab, "Live Video Mode")
        
        # Tab 3: Calibration
        calibration_tab = self._create_calibration_tab()
        self.tabs.addTab(calibration_tab, "Calibration")
        
        # Main splitter: tabs | inspector panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.tabs)
        
        # Inspector panel
        self.inspector = InspectorPanel()
        self._connect_inspector_signals()
        splitter.addWidget(self.inspector)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
    
    def _create_static_tab(self) -> QWidget:
        """Create static image analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top: Controls
        top_layout = QHBoxLayout()
        open_btn = QPushButton("Open Image")
        open_btn.clicked.connect(self._on_open_image)
        top_layout.addWidget(open_btn)
        
        # Rotation buttons
        self.rotate_ccw_btn = QPushButton("↺ 90°")
        self.rotate_ccw_btn.clicked.connect(lambda: self._rotate_image(-90))
        self.rotate_ccw_btn.setEnabled(False)
        top_layout.addWidget(self.rotate_ccw_btn)
        
        self.rotate_cw_btn = QPushButton("↻ 90°")
        self.rotate_cw_btn.clicked.connect(lambda: self._rotate_image(90))
        self.rotate_cw_btn.setEnabled(False)
        top_layout.addWidget(self.rotate_cw_btn)
        
        self.analyze_btn = QPushButton("Analyze Spectrum")
        self.analyze_btn.clicked.connect(self._on_analyze_static)
        self.analyze_btn.setEnabled(False)
        top_layout.addWidget(self.analyze_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # Image viewer and graph
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Image viewer
        self.static_image_viewer = ImageViewer()
        self.static_image_viewer.line_drawn.connect(self._on_line_drawn)
        content_splitter.addWidget(self.static_image_viewer)
        
        # Spectrum graph
        self.static_graph = SpectrumGraph()
        content_splitter.addWidget(self.static_graph)
        
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(content_splitter)
        
        return tab
    
    def _create_live_tab(self) -> QWidget:
        """Create live video mode tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Top: Connection controls
        top_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect Camera")
        self.connect_btn.clicked.connect(self._on_connect_camera)
        top_layout.addWidget(self.connect_btn)
        
        self.freeze_btn = QPushButton("Freeze Frame")
        self.freeze_btn.setEnabled(False)
        top_layout.addWidget(self.freeze_btn)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # Content
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Video viewer
        self.live_image_viewer = ImageViewer()
        content_splitter.addWidget(self.live_image_viewer)
        
        # Live graph
        self.live_graph = SpectrumGraph()
        content_splitter.addWidget(self.live_graph)
        
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 1)
        
        layout.addWidget(content_splitter)
        
        return tab
    
    def _create_calibration_tab(self) -> QWidget:
        """Create calibration tab."""
        self.calibration_widget = CalibrationWidget()
        self.calibration_widget.calibration_updated.connect(self._on_calibration_updated)
        return self.calibration_widget
    
    def _create_status_bar(self) -> None:
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _connect_inspector_signals(self) -> None:
        """Connect inspector panel signals."""
        self.inspector.thickness_changed.connect(self._on_thickness_changed)
        self.inspector.detection_mode_changed.connect(self._on_detection_mode_changed)
        self.inspector.show_smoothed_changed.connect(self._on_show_smoothed_changed)
        self.inspector.scale_changed.connect(self._on_scale_changed)
        self.inspector.savgol_params_changed.connect(self._on_savgol_changed)
    
    def _on_open_image(self) -> None:
        """Open an image file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Spectrum Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        
        if filename:
            try:
                # Load image
                image = cv2.imread(filename)
                if image is None:
                    raise ImageLoadError(filename)
                
                # Auto-rotate if vertical (height > width)
                h, w = image.shape[:2]
                if h > w:
                    logger.info(f"Auto-rotating vertical image ({h}x{w} -> {w}x{h})")
                    image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                    self.rotation_angle = 90
                else:
                    self.rotation_angle = 0
                
                self.current_image = image
                self.static_image_viewer.set_image(image)
                self.analyze_btn.setEnabled(True)
                self.rotate_ccw_btn.setEnabled(True)
                self.rotate_cw_btn.setEnabled(True)
                
                self.status_bar.showMessage(f"Loaded: {Path(filename).name}")
                self.inspector.set_status("Image loaded. Click and drag to draw line, or use auto-detect.")
                
                logger.info(f"Loaded image: {filename}")
                
            except Exception as e:
                error_msg = handle_error(e, logger)
                QMessageBox.critical(self, "Error", error_msg)
    
    def _rotate_image(self, angle_delta: int) -> None:
        """Rotate the current image."""
        if self.current_image is None:
            return
        
        # Apply rotation
        if angle_delta == 90:
            rotated = cv2.rotate(self.current_image, cv2.ROTATE_90_CLOCKWISE)
        elif angle_delta == -90:
            rotated = cv2.rotate(self.current_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return
        
        self.current_image = rotated
        self.rotation_angle = (self.rotation_angle + angle_delta) % 360
        
        # Update display
        self.static_image_viewer.set_image(rotated)
        self.static_image_viewer.clear_line()
        self.current_line_points = []
        
        logger.info(f"Rotated image by {angle_delta}°, total rotation: {self.rotation_angle}°")
        self.status_bar.showMessage(f"Rotated {angle_delta}° (total: {self.rotation_angle}°)")
    
    def _on_line_drawn(self, line_points: List[Tuple[int, int]]) -> None:
        """Handle line drawn by user."""
        self.current_line_points = line_points
        logger.info(f"User drew line: {line_points}")
        self.inspector.set_status(f"Line selected. Click 'Analyze Spectrum' to extract.")
    
    def _on_analyze_static(self) -> None:
        """Analyze static spectrum."""
        if self.current_image is None:
            return
        
        try:
            # Get line (auto or manual)
            mode = 'auto' if self.inspector.auto_radio.isChecked() else 'manual'
            
            if mode == 'auto':
                # Automatic detection
                result = self.line_detector.detect(self.current_image)
                if result is None:
                    raise NoSpectrumDetectedError()
                
                self.current_line_points = result.points
                logger.info(f"Auto-detected line: {self.current_line_points}")
            else:
                # Manual - user must draw line
                # For now, use a default horizontal line if none drawn
                if not self.current_line_points:
                    h, w = self.current_image.shape[:2]
                    y_center = h // 2
                    self.current_line_points = [(0, y_center), (w - 1, y_center)]
                    logger.info(f"Using default line: {self.current_line_points}")
            
            # Show line on image
            self.static_image_viewer.set_line(self.current_line_points, self.current_thickness)
            
            # Extract spectrum
            pixel_pos, intensity = self.spectrum_sampler.extract_cross_section(
                self.current_image,
                self.current_line_points,
                self.current_thickness
            )
            
            self.current_pixel_positions = pixel_pos
            self.current_intensity = intensity
            
            # Extract color strip
            color_strip = self.spectrum_sampler.extract_color_strip(
                self.current_image,
                self.current_line_points,
                self.current_thickness
            )
            
            # Apply calibration if available
            wavelengths = None
            if self.calibration_model and self.calibration_model.is_fitted():
                wavelengths = self.calibration_model.pixel_to_wavelength(pixel_pos)
            
            # Update graph
            self.static_graph.set_data(pixel_pos, intensity, wavelengths, color_strip)
            
            # Update calibration widget with intensity profile
            self.calibration_widget.set_intensity_profile(pixel_pos, intensity)
            
            self.status_bar.showMessage("Spectrum analyzed")
            self.inspector.set_status(f"Spectrum extracted ({len(intensity)} points)")
            
        except Exception as e:
            error_msg = handle_error(e, logger)
            QMessageBox.critical(self, "Error", error_msg)
    
    def _on_connect_camera(self) -> None:
        """Connect to camera."""
        if self.video_manager.is_connected():
            # Disconnect
            self.video_timer.stop()
            self.video_manager.disconnect()
            self.connect_btn.setText("Connect Camera")
            self.freeze_btn.setEnabled(False)
            self.status_bar.showMessage("Camera disconnected")
        else:
            # Connect
            try:
                from PySide6.QtWidgets import QInputDialog
                
                source, ok = QInputDialog.getInt(
                    self, "Camera Source",
                    "Enter camera index (0, 1, 2...) or use URL:",
                    0, 0, 10
                )
                
                if ok:
                    self.video_manager.connect(source)
                    self.video_timer.start(33)  # ~30 FPS
                    self.connect_btn.setText("Disconnect Camera")
                    self.freeze_btn.setEnabled(True)
                    self.status_bar.showMessage(f"Camera connected: {source}")
                    
            except Exception as e:
                error_msg = handle_error(e, logger)
                QMessageBox.critical(self, "Error", error_msg)
    
    def _update_video_frame(self) -> None:
        """Update video frame (called by timer)."""
        frame = self.video_manager.read_frame()
        if frame is None:
            return
        
        # Process frame
        processed_frame = self.frame_processor.process_frame(frame)
        
        # Display
        self.live_image_viewer.set_image(processed_frame)
        
        # Auto-analyze if line is set
        # (simplified - would need live line detection)
    
    def _on_thickness_changed(self, value: int) -> None:
        """Handle thickness change."""
        self.current_thickness = value
        if self.current_line_points:
            self.static_image_viewer.set_line(self.current_line_points, value)
    
    def _on_detection_mode_changed(self, mode: str) -> None:
        """Handle detection mode change."""
        logger.info(f"Detection mode: {mode}")
    
    def _on_show_smoothed_changed(self, show: bool) -> None:
        """Handle show smoothed toggle."""
        self.static_graph.set_show_smoothed(show)
        self.live_graph.set_show_smoothed(show)
    
    def _on_scale_changed(self, scale: str) -> None:
        """Handle scale change."""
        self.static_graph.set_scale(scale)
        self.live_graph.set_scale(scale)
    
    def _on_savgol_changed(self, window: int, order: int) -> None:
        """Handle Savitzky-Golay parameters change."""
        self.static_graph.set_smoothing_params(window, order)
        self.live_graph.set_smoothing_params(window, order)
    
    def _on_calibration_updated(self, model: CalibrationModel) -> None:
        """Handle calibration update."""
        self.calibration_model = model
        logger.info("Calibration updated")
        
        # Re-analyze if we have data
        if self.current_pixel_positions is not None:
            self._on_analyze_static()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Spectrum Analyzer",
            "<h3>Spectrum Analyzer</h3>"
            "<p>A production-grade application for spectrum analysis.</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Static image analysis</li>"
            "<li>Live video mode</li>"
            "<li>Wavelength calibration</li>"
            "<li>Automatic and manual line detection</li>"
            "</ul>"
        )
    
    def closeEvent(self, event) -> None:
        """Handle window close."""
        # Disconnect video
        if self.video_manager.is_connected():
            self.video_manager.disconnect()
        
        # Save config
        self.config.save()
        
        event.accept()
