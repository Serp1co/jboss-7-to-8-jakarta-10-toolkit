"""
BOM-aware POM dependency migrator for EAP 7 to EAP 8.
"""
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass, field

from source.migrators.base import BaseMigrator
from source.models.migrator import MigrationResult


@dataclass
class BOMInfo:
    """Information about a Bill of Materials."""
    group_id: str
    artifact_id: str
    version: Optional[str]
    key: str = field(init=False)
    
    def __post_init__(self):
        self.key = f"{self.group_id}:{self.artifact_id}"


class PomDependencyMigrator(BaseMigrator):
    """BOM-aware POM migrator for EAP 7 to EAP 8."""
    
    def __init__(self, config, logger=None):
        """Initialize the POM migrator."""
        super().__init__(config, logger)
        self.namespaces = {'maven': 'http://maven.apache.org/POM/4.0.0'}
        self.bom_config = self._load_bom_config()
        self.managed_dependencies = self._get_managed_dependencies()
    
    def can_handle(self, file_path: Path) -> bool:
        """Check if this migrator can handle the given file."""
        return file_path.name == 'pom.xml'
    
    def migrate_file(self, file_path: Path) -> MigrationResult:
        """Migrate a POM file."""
        result = MigrationResult(file_path=file_path, modified=False, replacements=0)
        
        try:
            # Register namespace to preserve in output
            ET.register_namespace('', self.namespaces['maven'])
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            replacement_details = []
            
            # Phase 1: Update dependencyManagement section (BOMs and regular dependencies)
            self.logger.debug("Phase 1: Updating dependencyManagement")
            dep_mgmt_changes = self._update_dependency_management(root)
            replacement_details.extend(dep_mgmt_changes)
            
            # Phase 2: Extract active BOMs
            active_boms = self._extract_active_boms(root)
            
            # Phase 3: Migrate regular dependencies
            self.logger.debug("Phase 2: Migrating dependencies")
            dep_changes = self._migrate_dependencies(root)
            replacement_details.extend(dep_changes)
            
            # Phase 4: Clean up versions for BOM-managed dependencies
            self.logger.debug("Phase 3: Cleaning up managed versions")
            version_changes = self._cleanup_managed_versions(root, active_boms)
            replacement_details.extend(version_changes)
            
            # Phase 5: Update properties
            self.logger.debug("Phase 4: Updating properties")
            prop_changes = self._update_properties(root)
            replacement_details.extend(prop_changes)
            
            # Phase 6: Update plugins if needed
            self.logger.debug("Phase 5: Updating plugins")
            plugin_changes = self._update_plugins(root)
            replacement_details.extend(plugin_changes)
            
            result.replacements = len(replacement_details)
            result.modified = result.replacements > 0
            result.details['replacements'] = replacement_details
            
            if result.modified:
                # Pretty print XML
                self._indent_xml(root)
                
                # Write changes
                content = ET.tostring(root, encoding='unicode', xml_declaration=True)
                if self._write_file(file_path, content):
                    if not self.config.dry_run:
                        self.logger.info(f"✓ Modified {file_path.name}: {result.replacements} changes")
                    else:
                        self.logger.info(f"[DRY-RUN] Would modify {file_path.name}: {result.replacements} changes")
                else:
                    result.errors.append(f"Failed to write file: {file_path}")
                    result.modified = False
            
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            self.logger.error(f"Failed to parse {file_path}: {e}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")
            self.logger.error(f"Error processing {file_path}: {e}")
        
        return result
    
    def _load_bom_config(self) -> Dict[str, Any]:
        """Load BOM configuration."""
        # Try to load from external file first
        config_path = Path(__file__).parent.parent.parent / "bom_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load BOM config: {e}")
        
        # Return default configuration
        return {
            "bom_rules": [
                {
                    "old": "org.jboss.bom:jboss-eap-jakartaee8",
                    "new": "org.jboss.bom:jboss-eap-ee:8.0.0.GA"
                },
                {
                    "old": "org.jboss.bom:jboss-eap-jakartaee8-with-tools",
                    "new": "org.jboss.bom:jboss-eap-ee-with-tools:8.0.0.GA"
                }
            ]
        }
    
    def _get_managed_dependencies(self) -> Set[str]:
        """Get the set of dependencies managed by EAP 8 BOMs."""
        # These are commonly managed by EAP BOMs
        return {
            # Jakarta EE APIs
            "jakarta.ejb:jakarta.ejb-api",
            "jakarta.servlet:jakarta.servlet-api",
            "jakarta.persistence:jakarta.persistence-api",
            "jakarta.validation:jakarta.validation-api",
            "jakarta.ws.rs:jakarta.ws.rs-api",
            "jakarta.enterprise:jakarta.enterprise.cdi-api",
            "jakarta.inject:jakarta.inject-api",
            "jakarta.faces:jakarta.faces-api",
            "jakarta.json:jakarta.json-api",
            "jakarta.xml.bind:jakarta.xml.bind-api",
            "jakarta.annotation:jakarta.annotation-api",
            "jakarta.transaction:jakarta.transaction-api",
            "jakarta.websocket:jakarta.websocket-api",
            "jakarta.jms:jakarta.jms-api",
            
            # Hibernate
            "org.hibernate.orm:hibernate-core",
            "org.hibernate:hibernate-core",
            "org.hibernate.validator:hibernate-validator",
            
            # RESTEasy
            "org.jboss.resteasy:resteasy-core",
            "org.jboss.resteasy:resteasy-client-api",
            
            # JBoss/WildFly
            "org.jboss.logging:jboss-logging",
            "org.wildfly.security:wildfly-elytron",
        }
    
    def _update_dependency_management(self, root: ET.Element) -> List[Dict]:
        """Update both BOMs and regular dependencies in dependencyManagement section."""
        changes = []
        
        dep_mgmt = root.find('.//maven:dependencyManagement', self.namespaces)
        if dep_mgmt is None:
            return changes
        
        dependencies = dep_mgmt.findall('.//maven:dependency', self.namespaces)
        
        for dep in dependencies:
            scope_elem = dep.find('maven:scope', self.namespaces)
            type_elem = dep.find('maven:type', self.namespaces)
            group_id = dep.find('maven:groupId', self.namespaces)
            artifact_id = dep.find('maven:artifactId', self.namespaces)
            version = dep.find('maven:version', self.namespaces)
            
            if group_id is None or artifact_id is None:
                continue
            
            old_key = f"{group_id.text}:{artifact_id.text}"
            
            # Check if it's a BOM (scope=import, type=pom)
            is_bom = (scope_elem is not None and scope_elem.text == 'import' and
                     type_elem is not None and type_elem.text == 'pom')
            
            # Check if this dependency needs migration
            if old_key in self.config.eap7_to_eap8_dependencies:
                mapping = self.config.eap7_to_eap8_dependencies[old_key]
                
                if 'new_artifact' in mapping:
                    new_group, new_artifact = mapping['new_artifact'].split(':')
                    
                    if group_id.text != new_group:
                        group_id.text = new_group
                    
                    if artifact_id.text != new_artifact:
                        artifact_id.text = new_artifact
                
                # For BOMs, we might want to update version
                # For regular dependencies in dependencyManagement, keep the version
                if is_bom and 'new_version' in mapping and version is not None:
                    # Only update BOM version if not a property reference
                    if not (version.text and version.text.startswith('${') and version.text.endswith('}')):
                        old_version = version.text
                        version.text = mapping['new_version']
                        
                        changes.append({
                            'type': 'bom_update',
                            'old': f"{old_key}:{old_version}",
                            'new': f"{mapping.get('new_artifact', old_key)}:{mapping['new_version']}"
                        })
                    else:
                        changes.append({
                            'type': 'bom_update',
                            'old': old_key,
                            'new': mapping.get('new_artifact', old_key),
                            'note': 'Version managed by property'
                        })
                else:
                    # Regular dependency in dependencyManagement
                    changes.append({
                        'type': 'dependency_management_update',
                        'old': old_key,
                        'new': mapping.get('new_artifact', old_key),
                        'version_kept': version.text if version is not None else 'none'
                    })
        
        return changes
    
    def _extract_active_boms(self, root: ET.Element) -> List[BOMInfo]:
        """Extract active BOMs from the POM."""
        boms = []
        
        dep_mgmt = root.find('.//maven:dependencyManagement', self.namespaces)
        if dep_mgmt is None:
            return boms
        
        dependencies = dep_mgmt.findall('.//maven:dependency', self.namespaces)
        
        for dep in dependencies:
            scope_elem = dep.find('maven:scope', self.namespaces)
            type_elem = dep.find('maven:type', self.namespaces)
            
            if (scope_elem is not None and scope_elem.text == 'import' and
                type_elem is not None and type_elem.text == 'pom'):
                
                group_id = dep.find('maven:groupId', self.namespaces)
                artifact_id = dep.find('maven:artifactId', self.namespaces)
                version = dep.find('maven:version', self.namespaces)
                
                if group_id is not None and artifact_id is not None:
                    bom = BOMInfo(
                        group_id=group_id.text,
                        artifact_id=artifact_id.text,
                        version=version.text if version is not None else None
                    )
                    boms.append(bom)
        
        return boms
    
    def _migrate_dependencies(self, root: ET.Element) -> List[Dict]:
        """Migrate dependency artifacts in the regular dependencies section."""
        changes = []
        
        # Find all dependencies (not in dependencyManagement)
        dependencies = root.findall('.//maven:dependencies/maven:dependency', self.namespaces)
        
        for dep in dependencies:
            # Skip dependencies that are inside dependencyManagement
            parent = dep
            while parent is not None:
                parent = parent.find('..')
                if parent is not None and parent.tag.endswith('dependencyManagement'):
                    break
            else:
                # This dependency is not in dependencyManagement
                group_id = dep.find('maven:groupId', self.namespaces)
                artifact_id = dep.find('maven:artifactId', self.namespaces)
                
                if group_id is not None and artifact_id is not None:
                    old_key = f"{group_id.text}:{artifact_id.text}"
                    
                    if old_key in self.config.eap7_to_eap8_dependencies:
                        mapping = self.config.eap7_to_eap8_dependencies[old_key]
                        
                        if 'new_artifact' in mapping:
                            new_group, new_artifact = mapping['new_artifact'].split(':')
                            
                            if group_id.text != new_group:
                                group_id.text = new_group
                            
                            if artifact_id.text != new_artifact:
                                artifact_id.text = new_artifact
                            
                            changes.append({
                                'type': 'dependency_migration',
                                'old': old_key,
                                'new': mapping['new_artifact']
                            })
        
        return changes
    
    def _cleanup_managed_versions(self, root: ET.Element, active_boms: List[BOMInfo]) -> List[Dict]:
        """Remove versions from dependencies managed by BOMs."""
        changes = []
        
        # Check if we have EAP BOMs
        has_eap_bom = any(
            'eap' in bom.artifact_id.lower() 
            for bom in active_boms
        )
        
        if not has_eap_bom:
            return changes
        
        # Only process regular dependencies (not in dependencyManagement)
        dependencies = root.findall('.//maven:dependencies/maven:dependency', self.namespaces)
        
        for dep in dependencies:
            # Skip dependencies inside dependencyManagement
            parent = dep
            while parent is not None:
                parent = parent.find('..')
                if parent is not None and parent.tag.endswith('dependencyManagement'):
                    break
            else:
                group_id = dep.find('maven:groupId', self.namespaces)
                artifact_id = dep.find('maven:artifactId', self.namespaces)
                version = dep.find('maven:version', self.namespaces)
                
                if group_id is not None and artifact_id is not None and version is not None:
                    dep_key = f"{group_id.text}:{artifact_id.text}"
                    
                    # Check if managed
                    if dep_key in self.managed_dependencies:
                        # Don't remove property references
                        if not (version.text and version.text.startswith('${') and version.text.endswith('}')):
                            old_version = version.text
                            dep.remove(version)
                            
                            changes.append({
                                'type': 'version_removed',
                                'dependency': dep_key,
                                'old_version': old_version,
                                'reason': 'Managed by BOM'
                            })
        
        return changes
    
    def _update_properties(self, root: ET.Element) -> List[Dict]:
        """Update properties in the POM."""
        changes = []
        
        properties = root.find('.//maven:properties', self.namespaces)
        if properties is not None:
            for prop in properties:
                prop_name = prop.tag.split('}')[-1]
                
                if prop.text:
                    old_text = prop.text
                    new_text = old_text
                    
                    # Update javax references
                    if 'javax' in new_text:
                        new_text = new_text.replace('javax.', 'jakarta.')
                    
                    # Update version properties
                    if 'version' in prop_name.lower():
                        if 'eap' in prop_name.lower() and '7.4' in new_text:
                            new_text = '8.0.0.GA'
                        elif 'hibernate' in prop_name.lower() and new_text.startswith('5.'):
                            new_text = '6.2.0.Final'
                        elif 'resteasy' in prop_name.lower() and (new_text.startswith('3.') or new_text.startswith('4.')):
                            new_text = '6.2.0.Final'
                    
                    if new_text != old_text:
                        prop.text = new_text
                        changes.append({
                            'type': 'property_update',
                            'name': prop_name,
                            'old': old_text,
                            'new': new_text
                        })
        
        return changes
    
    def _update_plugins(self, root: ET.Element) -> List[Dict]:
        """Update plugin configurations."""
        changes = []
        
        # Update maven-compiler-plugin
        compiler_plugins = root.findall('.//maven:plugin[maven:artifactId="maven-compiler-plugin"]', 
                                       self.namespaces)
        
        for plugin in compiler_plugins:
            config = plugin.find('maven:configuration', self.namespaces)
            if config is not None:
                source = config.find('maven:source', self.namespaces)
                target = config.find('maven:target', self.namespaces)
                
                if source is not None and target is not None:
                    if source.text in ['1.8', '8'] or target.text in ['1.8', '8']:
                        # Update to Java 11 (required by EAP 8)
                        config.remove(source)
                        config.remove(target)
                        
                        release = ET.SubElement(config, 'release')
                        release.text = '11'
                        
                        changes.append({
                            'type': 'plugin_update',
                            'plugin': 'maven-compiler-plugin',
                            'change': 'Updated to use release=11'
                        })
        
        return changes
    
    def _indent_xml(self, elem, level=0):
        """Pretty print XML."""
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