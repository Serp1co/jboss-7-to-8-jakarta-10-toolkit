"""
Migration engine that orchestrates the migration process.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from source.migrators.base import BaseMigrator
from source.migrators.java import JavaNamespaceMigrator
from source.migrators.pom import PomDependencyMigrator
from source.models.migrator import MigrationConfig, MigrationResult, MigrationType


class MigrationEngine:
    """Main engine to orchestrate migrations."""
    
    def __init__(self, config: MigrationConfig, logger: Optional[logging.Logger] = None):
        """Initialize the migration engine."""
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.migrators: List[BaseMigrator] = []
        
        # Register default migrators
        self._register_default_migrators()
    
    def _register_default_migrators(self):
        """Register the default set of migrators."""
        self.register_migrator(JavaNamespaceMigrator(self.config, self.logger))
        self.register_migrator(PomDependencyMigrator(self.config, self.logger))
    
    def register_migrator(self, migrator: BaseMigrator):
        """Register a new migrator."""
        self.migrators.append(migrator)
        self.logger.debug(f"Registered migrator: {migrator.__class__.__name__}")
    
    def migrate_directory(self, directory: Path, migration_types: Set[MigrationType]) -> Dict[str, Any]:
        """Migrate all applicable files in a directory."""
        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        results = []
        
        # Determine which migrators to use
        active_migrators = self._get_active_migrators(migration_types)
        
        if not active_migrators:
            self.logger.warning("No active migrators for the specified migration types")
            return self._generate_summary([])
        
        # Find all files
        self.logger.info("Scanning directory for files...")
        applicable_files = self._find_applicable_files(directory, active_migrators)
        
        if not applicable_files:
            self.logger.warning("No applicable files found for migration")
            return self._generate_summary([])
        
        self.logger.info(f"Found {len(applicable_files)} files to process")
        
        # Process files
        for i, (file_path, migrator) in enumerate(applicable_files, 1):
            relative_path = file_path.relative_to(directory)
            
            if self.config.verbose:
                self.logger.info(f"Processing [{i}/{len(applicable_files)}]: {relative_path}")
            else:
                # Show progress for non-verbose mode
                if i % 10 == 0 or i == len(applicable_files):
                    self.logger.info(f"Progress: {i}/{len(applicable_files)} files processed")
            
            try:
                result = migrator.migrate_file(file_path)
                results.append(result)
                
                if result.errors:
                    for error in result.errors:
                        self.logger.error(f"Error in {relative_path}: {error}")
            except Exception as e:
                self.logger.error(f"Unexpected error processing {relative_path}: {e}")
                # Create an error result
                error_result = MigrationResult(
                    file_path=file_path,
                    modified=False,
                    replacements=0,
                    errors=[str(e)]
                )
                results.append(error_result)
        
        # Generate summary
        return self._generate_summary(results)
    
    def _find_applicable_files(self, directory: Path, migrators: List[BaseMigrator]) -> List[tuple]:
        """Find all files that can be handled by the active migrators."""
        applicable_files = []
        
        # Use rglob to recursively find all files
        for file_path in directory.rglob("*"):
            # Skip directories and hidden files
            if not file_path.is_file():
                continue
            
            # Skip backup files
            if file_path.suffix == '.bak':
                continue
            
            # Skip hidden files and directories
            if any(part.startswith('.') for part in file_path.parts):
                continue
            
            # Check if any migrator can handle this file
            for migrator in migrators:
                if migrator.can_handle(file_path):
                    applicable_files.append((file_path, migrator))
                    break
        
        return applicable_files
    
    def _get_active_migrators(self, migration_types: Set[MigrationType]) -> List[BaseMigrator]:
        """Get migrators based on requested types."""
        if MigrationType.ALL in migration_types:
            return self.migrators
        
        active = []
        for migrator in self.migrators:
            # Check migrator type
            if (MigrationType.JAVA_NAMESPACE in migration_types and 
                isinstance(migrator, JavaNamespaceMigrator)):
                active.append(migrator)
            elif (MigrationType.POM_DEPENDENCY in migration_types and 
                  isinstance(migrator, PomDependencyMigrator)):
                active.append(migrator)
        
        return active
    
    def _generate_summary(self, results: List[MigrationResult]) -> Dict[str, Any]:
        """Generate migration summary."""
        summary = {
            'total_files': len(results),
            'modified_files': sum(1 for r in results if r.modified),
            'total_replacements': sum(r.replacements for r in results),
            'files_with_errors': sum(1 for r in results if r.errors),
            'by_type': {},
            'errors': []
        }
        
        # Collect errors
        for result in results:
            if result.errors:
                summary['errors'].append({
                    'file': str(result.file_path),
                    'errors': result.errors
                })
        
        # Group by file type
        for result in results:
            ext = result.file_path.suffix
            if ext not in summary['by_type']:
                summary['by_type'][ext] = {
                    'count': 0,
                    'modified': 0,
                    'replacements': 0
                }
            
            summary['by_type'][ext]['count'] += 1
            if result.modified:
                summary['by_type'][ext]['modified'] += 1
            summary['by_type'][ext]['replacements'] += result.replacements
        
        return summary