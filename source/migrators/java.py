from trio import Path
from source.migrators.base import BaseMigrator
from source.models.migrator import MigrationResult


class JavaNamespaceMigrator(BaseMigrator):
    """Migrator for Java namespace changes (javax to jakarta)."""
    
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix == '.java'
    
    def migrate_file(self, file_path: Path) -> MigrationResult:
        result = MigrationResult(file_path=file_path, modified=False, replacements=0)
        
        content = self._read_file(file_path)
        if content is None:
            result.errors.append("Failed to read file")
            return result
        
        original_content = content
        
        # Compile patterns
        import_pattern = re.compile(r'\b(import\s+(?:static\s+)?)(javax\.[a-zA-Z0-9_.]+)')
        package_pattern = re.compile(r'\b(package\s+)(javax\.[a-zA-Z0-9_.]+)')
        code_pattern = re.compile(r'\b(javax\.(?:[a-zA-Z0-9_]+\.)+[a-zA-Z0-9_]+)')
        
        replacement_details = []
        
        def should_replace(package: str) -> bool:
            for jakarta_package in self.config.javax_to_jakarta_packages:
                if package.startswith(jakarta_package):
                    return True
            return False
        
        def create_replacer(pattern_type: str):
            def replacer(match):
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
                        'new': new_package
                    })
                    if prefix:
                        return f"{prefix}{new_package}"
                    return new_package
                return match.group(0)
            return replacer
        
        # Apply replacements
        content = import_pattern.sub(create_replacer('import'), content)
        content = package_pattern.sub(create_replacer('package'), content)
        content = code_pattern.sub(create_replacer('code'), content)
        
        result.modified = content != original_content
        result.replacements = len(replacement_details)
        result.details['replacements'] = replacement_details
        
        if result.modified:
            if self._write_file(file_path, content):
                self.logger.info(f"Modified {file_path}: {result.replacements} replacements")
            else:
                result.errors.append("Failed to write file")
                result.modified = False
        
        return result
