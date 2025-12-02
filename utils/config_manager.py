"""
Configuration manager for application settings.

Handles loading, saving, and accessing configuration values.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration."""
    
    DEFAULT_CONFIG = {
        "app": {
            "theme": "dark",
            "window_geometry": None,
            "recent_files": [],
            "max_recent_files": 10
        },
        "processing": {
            "default_thickness": 5,
            "default_smoothing": 50,
            "background_removal": 0,
            "auto_detect": False
        },
        "calibration": {
            "polynomial_order": 2,
            "recent_profiles": [],
            "max_recent_profiles": 5
        },
        "video": {
            "default_source": 0,
            "fps_target": 30,
            "temporal_smoothing": 0.7
        },
        "graph": {
            "show_smoothed": True,
            "scale": "linear",
            "savgol_window": 11,
            "savgol_order": 3
        }
    }
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to config file (default: config/user_config.json)
        """
        if config_file is None:
            config_file = Path("config/user_config.json")
        
        self.config_file = config_file
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                
                # Merge with defaults (user config overrides defaults)
                self._merge_config(self.config, user_config)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
        else:
            logger.info("No config file found. Using defaults.")
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., "app.theme")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., "app.theme")
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    def add_recent_file(self, filepath: str) -> None:
        """
        Add a file to recent files list.
        
        Args:
            filepath: Path to file
        """
        recent = self.get("app.recent_files", [])
        
        # Remove if already exists
        if filepath in recent:
            recent.remove(filepath)
        
        # Add to front
        recent.insert(0, filepath)
        
        # Limit size
        max_recent = self.get("app.max_recent_files", 10)
        recent = recent[:max_recent]
        
        self.set("app.recent_files", recent)
    
    def _merge_config(self, base: Dict, override: Dict) -> None:
        """
        Recursively merge override config into base config.
        
        Args:
            base: Base configuration dict
            override: Override configuration dict
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
