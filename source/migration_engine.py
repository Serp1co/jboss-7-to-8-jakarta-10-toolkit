import logging
from typing import Any, Dict, List, Optional, Set

from trio import Path
from migrators.base import BaseMigrator
from migrators.java import JavaNamespaceMigrator
from migrators.pom import PomDependencyMigrator
from models.migrator import MigrationConfig, MigrationResult, MigrationType


class MigrationEngine:
    """Main engine to orchestrate migrations."""
    
    def __init__(self, config: MigrationConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.migrators: List[BaseMigrator] = []
        
        # Register default migrators
        self.register_migrator(JavaNamespaceMigrator(config, self.logger))
        self.register_migrator(PomDependencyMigrator(config, self.logger))
    
    def register_migrator(self, migrator: BaseMigrator):
        """Register a new migrator."""
        self.migrators.append(migrator)
        self.logger.debug(f"Registered migrator: {migrator.__class__.__name__}")
    
    def migrate_directory(self, directory: Path, migration_types: Set[MigrationType]) -> Dict[str, Any]:
        """Migrate all applicable files in a directory."""
        results = []
        
        # Determine which migrators to use
        active_migrators = self._get_active_migrators(migration_types)
        
        # Find all files
        all_files = list(directory.rglob("*"))
        applicable_files = []
        
        for file_path in all_files:
            if file_path.is_file():
                for migrator in active_migrators:
                    if migrator.can_handle(file_path):
                        applicable_files.append((file_path, migrator))
                        break
        
        self.logger.info(f"Found {len(applicable_files)} files to process")
        
        # Process files
        for file_path, migrator in applicable_files:
            relative_path = file_path.relative_to(directory)
            
            if self.config.verbose:
                self.logger.info(f"Processing: {relative_path}")
            
            result = migrator.migrate_file(file_path)
            results.append(result)
            
            if result.errors:
                for error in result.errors:
                    self.logger.error(f"Error in {relative_path}: {error}")
        
        # Generate summary
        return self._generate_summary(results)
    
    def _get_active_migrators(self, migration_types: Set[MigrationType]) -> List[BaseMigrator]:
        """Get migrators based on requested types."""
        if MigrationType.ALL in migration_types:
            return self.migrators
        
        active = []
        for migrator in self.migrators:
            if MigrationType.JAVA_NAMESPACE in migration_types and isinstance(migrator, JavaNamespaceMigrator):
                active.append(migrator)
            elif MigrationType.POM_DEPENDENCY in migration_types and isinstance(migrator, PomDependencyMigrator):
                active.append(migrator)
        
        return active
    
    def _generate_summary(self, results: List[MigrationResult]) -> Dict[str, Any]:
        """Generate migration summary."""
        summary = {
            'total_files': len(results),
            'modified_files': sum(1 for r in results if r.modified),
            'total_replacements': sum(r.replacements for r in results),
            'files_with_errors': sum(1 for r in results if r.errors),
            'by_type': {}
        }
        
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
