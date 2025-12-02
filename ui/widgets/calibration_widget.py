"""
Calibration widget for wavelength calibration.

Interface for adding calibration points and fitting.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QDoubleSpinBox, QSpinBox, QGroupBox,
    QMessageBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Signal
import numpy as np
import logging

from calibration import CalibrationModel, PeakDetector, ProfileManager

logger = logging.getLogger(__name__)


class CalibrationWidget(QWidget):
    """Calibration interface widget."""
    
    # Signals
    calibration_updated = Signal(object)  # Emits CalibrationModel
    
    def __init__(self, parent=None):
        """Initialize calibration widget."""
        super().__init__(parent)
        
        self.model = CalibrationModel()
        self.peak_detector = PeakDetector(prominence=0.1)
        self.profile_manager = ProfileManager()
        
        self.current_intensity: Optional[np.ndarray] = None
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Profile management
        profile_group = QGroupBox("Calibration Profiles")
        profile_layout = QHBoxLayout()
        
        self.profile_combo = QComboBox()
        self.load_btn = QPushButton("Load")
        self.save_btn = QPushButton("Save")
        
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addWidget(self.load_btn)
        profile_layout.addWidget(self.save_btn)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Add calibration point
        add_group = QGroupBox("Add Calibration Point")
        add_layout = QVBoxLayout()
        
        # Peak detection
        detect_layout = QHBoxLayout()
        self.detect_btn = QPushButton("Detect Peaks")
        detect_layout.addWidget(self.detect_btn)
        add_layout.addLayout(detect_layout)
        
        # Manual entry
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Pixel:"))
        self.pixel_spin = QDoubleSpinBox()
        self.pixel_spin.setRange(0, 10000)
        self.pixel_spin.setDecimals(2)
        manual_layout.addWidget(self.pixel_spin)
        
        manual_layout.addWidget(QLabel("Wavelength (nm):"))
        self.wavelength_spin = QDoubleSpinBox()
        self.wavelength_spin.setRange(200, 1000)
        self.wavelength_spin.setDecimals(1)
        manual_layout.addWidget(self.wavelength_spin)
        
        self.add_btn = QPushButton("Add Point")
        manual_layout.addWidget(self.add_btn)
        
        add_layout.addLayout(manual_layout)
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # Calibration points table
        table_group = QGroupBox("Calibration Points")
        table_layout = QVBoxLayout()
        
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(3)
        self.points_table.setHorizontalHeaderLabels(["Pixel", "Wavelength (nm)", ""])
        table_layout.addWidget(self.points_table)
        
        self.clear_btn = QPushButton("Clear All")
        table_layout.addWidget(self.clear_btn)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Fit controls
        fit_group = QGroupBox("Polynomial Fit")
        fit_layout = QVBoxLayout()
        
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("Polynomial Order:"))
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 3)
        self.order_spin.setValue(2)
        order_layout.addWidget(self.order_spin)
        order_layout.addStretch()
        
        fit_layout.addLayout(order_layout)
        
        self.fit_btn = QPushButton("Fit Calibration")
        fit_layout.addWidget(self.fit_btn)
        
        # Fit quality
        self.quality_label = QLabel("Not fitted")
        fit_layout.addWidget(self.quality_label)
        
        fit_group.setLayout(fit_layout)
        layout.addWidget(fit_group)
        
        # Connect signals
        self._connect_signals()
        
        # Load profiles
        self._refresh_profiles()
    
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.detect_btn.clicked.connect(self._on_detect_peaks)
        self.add_btn.clicked.connect(self._on_add_point)
        self.clear_btn.clicked.connect(self._on_clear_points)
        self.fit_btn.clicked.connect(self._on_fit)
        self.load_btn.clicked.connect(self._on_load_profile)
        self.save_btn.clicked.connect(self._on_save_profile)
    
    def set_intensity_profile(self, pixel_positions: np.ndarray, intensity: np.ndarray) -> None:
        """
        Set the current intensity profile for peak detection.
        
        Args:
            pixel_positions: Pixel positions
            intensity: Intensity values
        """
        self.current_intensity = intensity
        logger.info(f"Set intensity profile with {len(intensity)} points")
    
    def _on_detect_peaks(self) -> None:
        """Detect peaks in intensity profile."""
        if self.current_intensity is None:
            QMessageBox.warning(self, "No Data", "Please load a spectrum first.")
            return
        
        peaks = self.peak_detector.detect_peaks(self.current_intensity, max_peaks=5)
        
        if not peaks:
            QMessageBox.information(self, "No Peaks", "No peaks detected in the spectrum.")
            return
        
        # Show peak positions
        msg = "Detected peaks at pixel positions:\n\n"
        for i, peak in enumerate(peaks):
            msg += f"Peak {i+1}: {peak.position:.2f} (confidence: {peak.confidence:.2f})\n"
        
        QMessageBox.information(self, "Peaks Detected", msg)
        
        # Auto-fill first peak
        if peaks:
            self.pixel_spin.setValue(peaks[0].position)
    
    def _on_add_point(self) -> None:
        """Add calibration point."""
        pixel = self.pixel_spin.value()
        wavelength = self.wavelength_spin.value()
        
        self.model.add_point(pixel, wavelength)
        self._update_table()
    
    def _on_clear_points(self) -> None:
        """Clear all calibration points."""
        self.model.clear_points()
        self._update_table()
        self.quality_label.setText("Not fitted")
    
    def _on_fit(self) -> None:
        """Fit calibration model."""
        order = self.order_spin.value()
        
        if self.model.fit(order):
            quality = self.model.get_fit_quality()
            self.quality_label.setText(
                f"R² = {quality['r_squared']:.4f}, "
                f"RMSE = {quality['rmse']:.2f} nm"
            )
            
            # Emit signal
            self.calibration_updated.emit(self.model)
        else:
            QMessageBox.warning(
                self, "Fit Failed",
                "Failed to fit calibration. Need at least 2 points."
            )
    
    def _update_table(self) -> None:
        """Update calibration points table."""
        self.points_table.setRowCount(len(self.model.points))
        
        for i, point in enumerate(self.model.points):
            self.points_table.setItem(i, 0, QTableWidgetItem(f"{point.pixel:.2f}"))
            self.points_table.setItem(i, 1, QTableWidgetItem(f"{point.wavelength:.1f}"))
            
            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, idx=i: self._delete_point(idx))
            self.points_table.setCellWidget(i, 2, delete_btn)
    
    def _delete_point(self, index: int) -> None:
        """Delete a calibration point."""
        self.model.remove_point(index)
        self._update_table()
    
    def _refresh_profiles(self) -> None:
        """Refresh profile list."""
        self.profile_combo.clear()
        profiles = self.profile_manager.list_profiles()
        
        for profile in profiles:
            self.profile_combo.addItem(profile['name'])
    
    def _on_load_profile(self) -> None:
        """Load selected profile."""
        name = self.profile_combo.currentText()
        if not name:
            return
        
        try:
            self.model = self.profile_manager.load_profile(name)
            self._update_table()
            
            if self.model.is_fitted():
                quality = self.model.get_fit_quality()
                self.quality_label.setText(
                    f"R² = {quality['r_squared']:.4f}, "
                    f"RMSE = {quality['rmse']:.2f} nm"
                )
                self.calibration_updated.emit(self.model)
            
            QMessageBox.information(self, "Success", f"Loaded profile: {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load profile: {e}")
    
    def _on_save_profile(self) -> None:
        """Save current calibration."""
        from PySide6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if ok and name:
            try:
                self.profile_manager.save_profile(self.model, name)
                self._refresh_profiles()
                QMessageBox.information(self, "Success", f"Saved profile: {name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")
