"""
Profile manager for saving and loading calibration profiles.

Manages calibration profile persistence and library.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .calibration_model import CalibrationModel

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manage calibration profiles."""
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Initialize profile manager.
        
        Args:
            profiles_dir: Directory for storing profiles
                         (default: config/calibration_profiles)
        """
        if profiles_dir is None:
            profiles_dir = Path("config/calibration_profiles")
        
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def save_profile(
        self,
        model: CalibrationModel,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save a calibration profile.
        
        Args:
            model: Calibration model to save
            name: Profile name
            description: Optional description
            metadata: Optional metadata dict
            
        Returns:
            Path to saved profile file
        """
        # Create profile data
        profile_data = {
            'name': name,
            'description': description,
            'created': datetime.now().isoformat(),
            'metadata': metadata or {},
            'model': model.to_dict()
        }
        
        # Save to file
        filename = self._sanitize_filename(name) + '.json'
        filepath = self.profiles_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        logger.info(f"Saved calibration profile: {filepath}")
        
        return filepath
    
    def load_profile(self, name_or_path: str) -> CalibrationModel:
        """
        Load a calibration profile.
        
        Args:
            name_or_path: Profile name or full path
            
        Returns:
            Loaded CalibrationModel
            
        Raises:
            FileNotFoundError: If profile not found
            ValueError: If profile is invalid
        """
        # Try as path first
        filepath = Path(name_or_path)
        if not filepath.exists():
            # Try as profile name
            filename = self._sanitize_filename(name_or_path) + '.json'
            filepath = self.profiles_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Profile not found: {name_or_path}")
        
        # Load profile data
        with open(filepath, 'r') as f:
            profile_data = json.load(f)
        
        # Reconstruct model
        model = CalibrationModel.from_dict(profile_data['model'])
        
        logger.info(f"Loaded calibration profile: {filepath}")
        
        return model
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        List all available calibration profiles.
        
        Returns:
            List of profile info dicts with 'name', 'description', 'created', 'path'
        """
        profiles = []
        
        for filepath in self.profiles_dir.glob('*.json'):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                profiles.append({
                    'name': data.get('name', filepath.stem),
                    'description': data.get('description', ''),
                    'created': data.get('created', ''),
                    'path': str(filepath),
                    'num_points': len(data['model'].get('points', []))
                })
            except Exception as e:
                logger.warning(f"Failed to read profile {filepath}: {e}")
        
        # Sort by creation date (newest first)
        profiles.sort(key=lambda p: p.get('created', ''), reverse=True)
        
        return profiles
    
    def delete_profile(self, name_or_path: str) -> None:
        """
        Delete a calibration profile.
        
        Args:
            name_or_path: Profile name or full path
        """
        # Try as path first
        filepath = Path(name_or_path)
        if not filepath.exists():
            # Try as profile name
            filename = self._sanitize_filename(name_or_path) + '.json'
            filepath = self.profiles_dir / filename
        
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deleted calibration profile: {filepath}")
        else:
            logger.warning(f"Profile not found: {name_or_path}")
    
    def export_profile(self, name_or_path: str, export_path: Path) -> None:
        """
        Export a profile to a different location.
        
        Args:
            name_or_path: Profile name or path to export
            export_path: Destination path
        """
        # Load profile
        model = self.load_profile(name_or_path)
        
        # Get original data for metadata
        filepath = Path(name_or_path)
        if not filepath.exists():
            filename = self._sanitize_filename(name_or_path) + '.json'
            filepath = self.profiles_dir / filename
        
        with open(filepath, 'r') as f:
            profile_data = json.load(f)
        
        # Save to export path
        with open(export_path, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        logger.info(f"Exported profile to: {export_path}")
    
    def import_profile(self, import_path: Path, name: Optional[str] = None) -> None:
        """
        Import a profile from an external file.
        
        Args:
            import_path: Path to profile file
            name: Optional new name (default: use original name)
        """
        with open(import_path, 'r') as f:
            profile_data = json.load(f)
        
        # Use new name if provided
        if name is not None:
            profile_data['name'] = name
        
        # Save to profiles directory
        profile_name = profile_data.get('name', import_path.stem)
        filename = self._sanitize_filename(profile_name) + '.json'
        filepath = self.profiles_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(profile_data, f, indent=2)
        
        logger.info(f"Imported profile: {filepath}")
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a profile name for use as filename.
        
        Args:
            name: Profile name
            
        Returns:
            Sanitized filename (without extension)
        """
        # Replace unsafe characters
        safe_name = name.replace('/', '_').replace('\\', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in '._- ')
        safe_name = safe_name.strip()
        
        return safe_name or 'unnamed_profile'
