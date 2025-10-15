import abc
import logging
from typing import Optional

from trio import Path
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
    
    def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None
    
    def _write_file(self, file_path: Path, content: str) -> bool:
        """Write file content with error handling and backup."""
        try:
            if self.config.backup and not self.config.dry_run:
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                import shutil
                shutil.copy2(file_path, backup_path)
                self.logger.debug(f"Created backup: {backup_path}")
            
            if not self.config.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Error writing {file_path}: {e}")
            return False
