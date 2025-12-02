"""
Inspector panel with all processing controls.

Right-side panel with sliders and toggles for spectrum processing.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QRadioButton, QButtonGroup, QCheckBox,
    QSpinBox, QGroupBox, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, Signal
import logging

logger = logging.getLogger(__name__)


class InspectorPanel(QWidget):
    """Inspector panel with processing controls."""
    
    # Signals
    thickness_changed = Signal(int)
    smoothing_changed = Signal(int)
    background_removal_changed = Signal(int)
    detection_mode_changed = Signal(str)  # 'manual' or 'auto'
    show_smoothed_changed = Signal(bool)
    scale_changed = Signal(str)  # 'linear' or 'log'
    savgol_params_changed = Signal(int, int)  # window, order
    
    def __init__(self, parent=None):
        """Initialize inspector panel."""
        super().__init__(parent)
        
        self.setMinimumWidth(280)
        self.setMaximumWidth(350)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Line Selection Mode
        mode_group = QGroupBox("Line Selection Mode")
        mode_layout = QVBoxLayout()
        
        self.manual_radio = QRadioButton("Manual")
        self.auto_radio = QRadioButton("Automatic")
        self.manual_radio.setChecked(True)
        
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.manual_radio, 0)
        self.mode_group.addButton(self.auto_radio, 1)
        
        mode_layout.addWidget(self.manual_radio)
        mode_layout.addWidget(self.auto_radio)
        mode_group.setLayout(mode_layout)
        
        layout.addWidget(mode_group)
        
        # Connect mode change
        self.manual_radio.toggled.connect(self._on_mode_changed)
        
        # Sampling Parameters
        sampling_group = QGroupBox("Sampling Parameters")
        sampling_layout = QVBoxLayout()
        
        # Thickness slider
        thickness_label = QLabel("Thickness (pixels):")
        self.thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.thickness_slider.setRange(1, 20)
        self.thickness_slider.setValue(5)
        self.thickness_value_label = QLabel("5")
        
        thickness_row = QHBoxLayout()
        thickness_row.addWidget(thickness_label)
        thickness_row.addStretch()
        thickness_row.addWidget(self.thickness_value_label)
        
        sampling_layout.addLayout(thickness_row)
        sampling_layout.addWidget(self.thickness_slider)
        
        # Smoothing slider
        smoothing_label = QLabel("Smoothing Strength:")
        self.smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.smoothing_slider.setRange(0, 100)
        self.smoothing_slider.setValue(50)
        self.smoothing_value_label = QLabel("50%")
        
        smoothing_row = QHBoxLayout()
        smoothing_row.addWidget(smoothing_label)
        smoothing_row.addStretch()
        smoothing_row.addWidget(self.smoothing_value_label)
        
        sampling_layout.addLayout(smoothing_row)
        sampling_layout.addWidget(self.smoothing_slider)
        
        # Background removal slider
        bg_label = QLabel("Background Removal:")
        self.bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_slider.setRange(0, 100)
        self.bg_slider.setValue(0)
        self.bg_value_label = QLabel("0%")
        
        bg_row = QHBoxLayout()
        bg_row.addWidget(bg_label)
        bg_row.addStretch()
        bg_row.addWidget(self.bg_value_label)
        
        sampling_layout.addLayout(bg_row)
        sampling_layout.addWidget(self.bg_slider)
        
        sampling_group.setLayout(sampling_layout)
        layout.addWidget(sampling_group)
        
        # Graph Settings
        graph_group = QGroupBox("Graph Settings")
        graph_layout = QVBoxLayout()
        
        # Show smoothed toggle
        self.show_smoothed_check = QCheckBox("Show Smoothed Curve")
        self.show_smoothed_check.setChecked(True)
        graph_layout.addWidget(self.show_smoothed_check)
        
        # Scale selection
        scale_label = QLabel("Y-Scale:")
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Linear", "Logarithmic"])
        
        scale_row = QHBoxLayout()
        scale_row.addWidget(scale_label)
        scale_row.addWidget(self.scale_combo)
        
        graph_layout.addLayout(scale_row)
        
        # Savitzky-Golay window
        savgol_label = QLabel("Smoothing Window:")
        self.savgol_window = QSpinBox()
        self.savgol_window.setRange(3, 51)
        self.savgol_window.setSingleStep(2)
        self.savgol_window.setValue(11)
        
        savgol_row = QHBoxLayout()
        savgol_row.addWidget(savgol_label)
        savgol_row.addWidget(self.savgol_window)
        
        graph_layout.addLayout(savgol_row)
        
        graph_group.setLayout(graph_layout)
        layout.addWidget(graph_group)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("No spectrum loaded")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Stretch at bottom
        layout.addStretch()
        
        # Connect signals
        self._connect_signals()
    
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.thickness_slider.valueChanged.connect(self._on_thickness_changed)
        self.smoothing_slider.valueChanged.connect(self._on_smoothing_changed)
        self.bg_slider.valueChanged.connect(self._on_bg_changed)
        self.show_smoothed_check.toggled.connect(self.show_smoothed_changed)
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        self.savgol_window.valueChanged.connect(self._on_savgol_changed)
    
    def _on_thickness_changed(self, value: int) -> None:
        """Handle thickness slider change."""
        self.thickness_value_label.setText(str(value))
        self.thickness_changed.emit(value)
    
    def _on_smoothing_changed(self, value: int) -> None:
        """Handle smoothing slider change."""
        self.smoothing_value_label.setText(f"{value}%")
        self.smoothing_changed.emit(value)
    
    def _on_bg_changed(self, value: int) -> None:
        """Handle background removal slider change."""
        self.bg_value_label.setText(f"{value}%")
        self.background_removal_changed.emit(value)
    
    def _on_mode_changed(self) -> None:
        """Handle detection mode change."""
        mode = 'manual' if self.manual_radio.isChecked() else 'auto'
        self.detection_mode_changed.emit(mode)
    
    def _on_scale_changed(self, text: str) -> None:
        """Handle scale change."""
        scale = 'linear' if text == 'Linear' else 'log'
        self.scale_changed.emit(scale)
    
    def _on_savgol_changed(self, value: int) -> None:
        """Handle Savitzky-Golay window change."""
        # Ensure odd
        if value % 2 == 0:
            value += 1
            self.savgol_window.setValue(value)
        
        order = 3  # Fixed order for now
        self.savgol_params_changed.emit(value, order)
    
    def set_status(self, text: str) -> None:
        """
        Set status text.
        
        Args:
            text: Status text
        """
        self.status_label.setText(text)
