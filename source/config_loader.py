"""
Configuration loader for the migration framework.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from source.models.migrator import MigrationConfig


class ConfigurationLoader:
    """Load configuration from various sources."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> MigrationConfig:
        """Load configuration from JSON file."""
        config = MigrationConfig()
        
        if not config_path.exists():
            return config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # Update config with loaded data
            if 'javax_to_jakarta_packages' in config_data:
                config.javax_to_jakarta_packages = set(config_data['javax_to_jakarta_packages'])
            
            if 'eap7_to_eap8_dependencies' in config_data:
                config.eap7_to_eap8_dependencies = config_data['eap7_to_eap8_dependencies']
            
            if 'dry_run' in config_data:
                config.dry_run = config_data['dry_run']
            
            if 'verbose' in config_data:
                config.verbose = config_data['verbose']
            
            if 'backup' in config_data:
                config.backup = config_data['backup']
                
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON config file {config_path}: {e}")
        except Exception as e:
            logging.error(f"Error loading config file {config_path}: {e}")
        
        return config
    
    @classmethod
    def save_default_config(cls, config_path: Path) -> bool:
        """Save default configuration to file."""
        config = MigrationConfig()
        config_data = {
            'dry_run': config.dry_run,
            'verbose': config.verbose,
            'backup': config.backup,
            'javax_to_jakarta_packages': sorted(list(config.javax_to_jakarta_packages)),
            'eap7_to_eap8_dependencies': config.eap7_to_eap8_dependencies
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, sort_keys=False)
            return True
        except Exception as e:
            logging.error(f"Error saving config file {config_path}: {e}")
            return False