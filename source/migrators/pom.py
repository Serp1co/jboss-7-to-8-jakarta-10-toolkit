import logging
from typing import Optional

from trio import Path
from source.migrators.base import BaseMigrator
from source.models.migrator import MigrationConfig, MigrationResult
import xml.etree.ElementTree as ET


class PomDependencyMigrator(BaseMigrator):
    """Migrator for POM dependency changes (EAP 7 to EAP 8)."""
    
    def __init__(self, config: MigrationConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
    
    def can_handle(self, file_path: Path) -> bool:
        return file_path.name == 'pom.xml'
    
    def migrate_file(self, file_path: Path) -> MigrationResult:
        result = MigrationResult(file_path=file_path, modified=False, replacements=0)
        
        try:
            # Parse XML with namespace handling
            ET.register_namespace('', self.namespaces['maven'])
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            replacement_details = []
            
            # Process dependencies
            dependencies = root.findall('.//maven:dependency', self.namespaces)
            for dep in dependencies:
                group_id_elem = dep.find('maven:groupId', self.namespaces)
                artifact_id_elem = dep.find('maven:artifactId', self.namespaces)
                version_elem = dep.find('maven:version', self.namespaces)
                
                if group_id_elem is not None and artifact_id_elem is not None:
                    old_key = f"{group_id_elem.text}:{artifact_id_elem.text}"
                    
                    if old_key in self.config.eap7_to_eap8_dependencies:
                        mapping = self.config.eap7_to_eap8_dependencies[old_key]
                        
                        detail = {
                            'old_dependency': old_key,
                            'changes': []
                        }
                        
                        # Update artifact if specified
                        if 'new_artifact' in mapping:
                            new_group, new_artifact = mapping['new_artifact'].split(':')
                            group_id_elem.text = new_group
                            artifact_id_elem.text = new_artifact
                            detail['changes'].append(f"artifact: {old_key} -> {mapping['new_artifact']}")
                        
                        # Update version if specified
                        if 'new_version' in mapping and version_elem is not None:
                            old_version = version_elem.text
                            version_elem.text = mapping['new_version']
                            detail['changes'].append(f"version: {old_version} -> {mapping['new_version']}")
                        
                        replacement_details.append(detail)
            
            # Also migrate javax namespace references in properties
            properties = root.find('.//maven:properties', self.namespaces)
            if properties is not None:
                for prop in properties:
                    if prop.text and 'javax' in prop.text:
                        new_text = prop.text.replace('javax.', 'jakarta.')
                        if new_text != prop.text:
                            replacement_details.append({
                                'property': prop.tag.split('}')[-1],
                                'old_value': prop.text,
                                'new_value': new_text
                            })
                            prop.text = new_text
            
            result.replacements = len(replacement_details)
            result.modified = result.replacements > 0
            result.details['replacements'] = replacement_details
            
            if result.modified and not self.config.dry_run:
                # Pretty print XML
                self._indent_xml(root)
                tree.write(file_path, encoding='utf-8', xml_declaration=True)
                self.logger.info(f"Modified {file_path}: {result.replacements} dependency changes")
            
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            self.logger.error(f"Failed to parse {file_path}: {e}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")
            self.logger.error(f"Error processing {file_path}: {e}")
        
        return result
    
    def _indent_xml(self, elem, level=0):
        """Add pretty printing to XML."""
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent
