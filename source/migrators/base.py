"""
Base migrator class for all migration implementations.
"""
import abc
import logging
import shutil
from pathlib import Path
from typing import Optional

from source.models.migrator import MigrationConfig, MigrationResult


class BaseMigrator(abc.ABC):
    """Abstract base class for all migrators."""
    
    def __init__(self, config: MigrationConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    @abc.abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if this migrator can handle the given file."""
        pass
    
    @abc.abstractmethod
    def migrate_file(self, file_path: Path) -> MigrationResult:
        """Perform migration on a single file."""
        pass
    
    def _read_file(self, file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """Read file content with error handling."""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    self.logger.warning(f"File {file_path} read with latin-1 encoding")
                    return f.read()
            except Exception as e:
                self.logger.error(f"Error reading {file_path} with fallback encoding: {e}")
                return None
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def _write_file(self, file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
        """Write file content with error handling and backup."""
        try:
            # Create backup if requested
            if self.config.backup and not self.config.dry_run:
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                try:
                    shutil.copy2(file_path, backup_path)
                    self.logger.debug(f"Created backup: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"Could not create backup for {file_path}: {e}")
            
            # Write file if not in dry-run mode
            if not self.config.dry_run:
                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
                    
                self.logger.debug(f"Successfully wrote {file_path}")
            else:
                self.logger.debug(f"[DRY-RUN] Would write {file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing {file_path}: {e}")
            return False