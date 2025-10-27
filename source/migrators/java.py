"""
Java namespace migrator for javax to jakarta migration.
"""
import re
from pathlib import Path
from typing import Dict, List

from source.migrators.base import BaseMigrator
from source.models.migrator import MigrationResult


class JavaNamespaceMigrator(BaseMigrator):
    """Migrator for Java namespace changes (javax to jakarta)."""
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if this migrator can handle the given file."""
        return file_path.suffix == '.java'
    
    def migrate_file(self, file_path: Path) -> MigrationResult:
        """Migrate javax namespaces to jakarta in a Java file."""
        result = MigrationResult(file_path=file_path, modified=False, replacements=0)
        
        # Read file content
        content = self._read_file(file_path)
        if content is None:
            result.errors.append(f"Failed to read file: {file_path}")
            return result
        
        original_content = content
        
        # Compile regex patterns for efficiency
        patterns = {
            'import': re.compile(r'\b(import\s+(?:static\s+)?)(javax\.[a-zA-Z0-9_.]+)'),
            'package': re.compile(r'\b(package\s+)(javax\.[a-zA-Z0-9_.]+)'),
            'code': re.compile(r'\b(javax\.(?:[a-zA-Z0-9_]+\.)+[a-zA-Z0-9_]+)')
        }
        
        replacement_details = []
        
        def should_replace(package: str) -> bool:
            """Check if a javax package should be replaced with jakarta."""
            for jakarta_package in self.config.javax_to_jakarta_packages:
                if package.startswith(jakarta_package):
                    return True
            return False
        
        def create_replacer(pattern_type: str):
            """Create a replacer function for the given pattern type."""
            def replacer(match):
                nonlocal replacement_details
                
                if pattern_type in ['import', 'package']:
                    prefix = match.group(1)
                    package = match.group(2)
                else:  # code reference
                    prefix = ''
                    package = match.group(1)
                
                if should_replace(package):
                    new_package = package.replace('javax.', 'jakarta.', 1)
                    replacement_details.append({
                        'type': pattern_type,
                        'old': package,
                        'new': new_package,
                        'line': content[:match.start()].count('\n') + 1
                    })
                    
                    if self.config.verbose:
                        self.logger.debug(f"  {pattern_type}: {package} → {new_package}")
                    
                    if prefix:
                        return f"{prefix}{new_package}"
                    return new_package
                
                return match.group(0)
            
            return replacer
        
        # Apply replacements in order
        for pattern_type, pattern in patterns.items():
            content = pattern.sub(create_replacer(pattern_type), content)
        
        # Check if file was modified
        result.modified = content != original_content
        result.replacements = len(replacement_details)
        result.details['replacements'] = replacement_details
        
        if result.modified:
            # Write the modified content
            if self._write_file(file_path, content):
                if not self.config.dry_run:
                    self.logger.info(f"✓ Modified {file_path.name}: {result.replacements} replacements")
                else:
                    self.logger.info(f"[DRY-RUN] Would modify {file_path.name}: {result.replacements} replacements")
            else:
                result.errors.append(f"Failed to write file: {file_path}")
                result.modified = False
        
        return result