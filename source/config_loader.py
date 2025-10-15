import json
from trio import Path

from models.migrator import MigrationConfig


class ConfigurationLoader:
    """Load configuration from various sources."""
    
    @staticmethod
    def load_from_file(config_path: Path) -> MigrationConfig:
        """Load configuration from JSON file."""
        config = MigrationConfig()
        
        if config_path.exists():
            with open(config_path, 'r') as f:
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
        
        return config
    
    @staticmethod
    def save_default_config(config_path: Path):
        """Save default configuration to file."""
        config = MigrationConfig()
        config_data = {
            'javax_to_jakarta_packages': list(config.javax_to_jakarta_packages),
            'eap7_to_eap8_dependencies': config.eap7_to_eap8_dependencies,
            'dry_run': config.dry_run,
            'verbose': config.verbose,
            'backup': config.backup
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
