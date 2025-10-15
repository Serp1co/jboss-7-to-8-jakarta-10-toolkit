from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set

from trio import Path

class MigrationType(Enum):
    """Types of migrations supported."""
    JAVA_NAMESPACE = "java_namespace"
    POM_DEPENDENCY = "pom_dependency"
    ALL = "all"


@dataclass
class MigrationResult:
    """Result of a single file migration."""
    file_path: Path
    modified: bool
    replacements: int
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationConfig:
    """Configuration for migrations."""
    dry_run: bool = False
    verbose: bool = False
    backup: bool = True
    
    # Java migration specific
    javax_to_jakarta_packages: Set[str] = field(default_factory=lambda: {
        'javax.activation',
        'javax.annotation',
        'javax.batch',
        'javax.decorator',
        'javax.ejb',
        'javax.el',
        'javax.enterprise',
        'javax.faces',
        'javax.inject',
        'javax.interceptor',
        'javax.jms',
        'javax.json',
        'javax.jws',
        'javax.mail',
        'javax.persistence',
        'javax.resource',
        'javax.security.auth.message',
        'javax.security.enterprise',
        'javax.security.jacc',
        'javax.servlet',
        'javax.transaction',
        'javax.validation',
        'javax.websocket',
        'javax.ws.rs',
        'javax.xml.bind',
        'javax.xml.soap',
        'javax.xml.ws'
    })
    
    # POM migration specific - EAP 7 to EAP 8 dependency mappings
    eap7_to_eap8_dependencies: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        # Example mappings - extend as needed
        'org.jboss.bom:jboss-eap-jakartaee8': {
            'new_artifact': 'org.jboss.bom:jboss-eap-ee',
            'new_version': '8.0.0.GA'
        },
        'org.jboss.spec.javax.ejb:jboss-ejb-api_3.2_spec': {
            'new_artifact': 'jakarta.ejb:jakarta.ejb-api',
            'new_version': '4.0.1'
        },
        'org.jboss.spec.javax.servlet:jboss-servlet-api_4.0_spec': {
            'new_artifact': 'jakarta.servlet:jakarta.servlet-api',
            'new_version': '6.0.0'
        },
        'org.hibernate:hibernate-core': {
            'new_version': '6.2.0.Final'  # Version update only
        },
        'org.hibernate.validator:hibernate-validator': {
            'new_version': '8.0.0.Final'
        }
    })
