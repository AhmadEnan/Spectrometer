"""
Calibration marker dialog for visual calibration.

Quick input dialog when user clicks on a spectrum peak.
"""

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QLineEdit, QPushButton, QComboBox,
    QDialogButtonBox
)
from PySide6.QtCore import Qt


class CalibrationMarkerDialog(QDialog):
    """Dialog for entering wavelength when clicking on spectrum."""
    
    # Common laser wavelengths for quick selection
    COMMON_WAVELENGTHS = {
        "Custom": 0,
        "UV 365nm": 365,
        "Violet 405nm": 405,
        "Blue 445nm": 445,
        "Blue 473nm": 473,
        "Green 532nm": 532,
        "Yellow 589nm": 589,
        "Red 632.8nm (HeNe)": 632.8,
        "Red 650nm": 650,
        "Red 660nm": 660,
        "IR 780nm": 780,
        "IR 808nm": 808,
    }
    
    def __init__(self, pixel_position: float, parent=None):
        """
        Initialize calibration marker dialog.
        
        Args:
            pixel_position: Pixel position where user clicked
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.pixel_position = pixel_position
        self.setWindowTitle("Add Calibration Point")
        self.setModal(True)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(f"Pixel position: <b>{pixel_position:.2f}</b>")
        layout.addWidget(info_label)
        
        # Quick select common wavelengths
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick Select:"))
        
        self.wavelength_combo = QComboBox()
        for name in self.COMMON_WAVELENGTHS.keys():
            self.wavelength_combo.addItem(name)
        self.wavelength_combo.currentTextChanged.connect(self._on_quick_select)
        quick_layout.addWidget(self.wavelength_combo)
        
        layout.addLayout(quick_layout)
        
        # Wavelength input
        wl_layout = QHBoxLayout()
        wl_layout.addWidget(QLabel("Wavelength (nm):"))
        
        self.wavelength_spin = QDoubleSpinBox()
        self.wavelength_spin.setRange(200, 2000)
        self.wavelength_spin.setDecimals(1)
        self.wavelength_spin.setValue(532.0)  # Default green laser
        self.wavelength_spin.setSingleStep(1.0)
        self.wavelength_spin.setMinimumWidth(120)
        wl_layout.addWidget(self.wavelength_spin)
        
        layout.addLayout(wl_layout)
        
        # Optional label
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Label (optional):"))
        
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g., Green Laser")
        label_layout.addWidget(self.label_edit)
        
        layout.addLayout(label_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Focus on wavelength input
        self.wavelength_spin.setFocus()
        self.wavelength_spin.selectAll()
    
    def _on_quick_select(self, name: str) -> None:
        """Handle quick wavelength selection."""
        wavelength = self.COMMON_WAVELENGTHS.get(name, 0)
        if wavelength > 0:
            self.wavelength_spin.setValue(wavelength)
            # Auto-fill label if empty
            if not self.label_edit.text():
                self.label_edit.setText(name)
    
    def get_values(self) -> Tuple[float, float, str]:
        """
        Get entered values.
        
        Returns:
            Tuple of (pixel_position, wavelength, label)
        """
        return (
            self.pixel_position,
            self.wavelength_spin.value(),
            self.label_edit.text()
        )
