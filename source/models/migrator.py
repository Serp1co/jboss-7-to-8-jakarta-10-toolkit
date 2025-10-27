"""
Data models for the migration framework.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Set


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
        # BOMs
        'org.jboss.bom:jboss-eap-jakartaee8': {
            'new_artifact': 'org.jboss.bom:jboss-eap-ee',
            'new_version': '8.0.0.GA'
        },
        'org.jboss.bom:jboss-eap-jakartaee8-with-tools': {
            'new_artifact': 'org.jboss.bom:jboss-eap-ee-with-tools',
            'new_version': '8.0.0.GA'
        },
        
        # JBoss Spec to Jakarta
        'org.jboss.spec.javax.ejb:jboss-ejb-api_3.2_spec': {
            'new_artifact': 'jakarta.ejb:jakarta.ejb-api',
            'new_version': '4.0.1'
        },
        'org.jboss.spec.javax.servlet:jboss-servlet-api_4.0_spec': {
            'new_artifact': 'jakarta.servlet:jakarta.servlet-api',
            'new_version': '6.0.0'
        },
        'org.jboss.spec.javax.ws.rs:jboss-jaxrs-api_2.1_spec': {
            'new_artifact': 'jakarta.ws.rs:jakarta.ws.rs-api',
            'new_version': '3.1.0'
        },
        'org.jboss.spec.javax.xml.bind:jboss-jaxb-api_2.3_spec': {
            'new_artifact': 'jakarta.xml.bind:jakarta.xml.bind-api',
            'new_version': '4.0.0'
        },
        'org.jboss.spec.javax.faces:jboss-jsf-api_2.3_spec': {
            'new_artifact': 'jakarta.faces:jakarta.faces-api',
            'new_version': '4.0.1'
        },
        'org.jboss.spec.javax.annotation:jboss-annotations-api_1.3_spec': {
            'new_artifact': 'jakarta.annotation:jakarta.annotation-api',
            'new_version': '2.1.1'
        },
        'org.jboss.spec.javax.transaction:jboss-transaction-api_1.3_spec': {
            'new_artifact': 'jakarta.transaction:jakarta.transaction-api',
            'new_version': '2.0.1'
        },
        'org.jboss.spec.javax.json:jboss-json-api_1.1_spec': {
            'new_artifact': 'jakarta.json:jakarta.json-api',
            'new_version': '2.1.1'
        },
        
        # Hibernate
        'org.hibernate:hibernate-core': {
            'new_version': '6.2.0.Final'
        },
        'org.hibernate:hibernate-entitymanager': {
            'new_artifact': 'org.hibernate.orm:hibernate-core',
            'new_version': '6.2.0.Final'
        },
        'org.hibernate.validator:hibernate-validator': {
            'new_version': '8.0.0.Final'
        },
        
        # RESTEasy
        'org.jboss.resteasy:resteasy-jaxrs': {
            'new_artifact': 'org.jboss.resteasy:resteasy-core',
            'new_version': '6.2.0.Final'
        },
        'org.jboss.resteasy:resteasy-client': {
            'new_artifact': 'org.jboss.resteasy:resteasy-client-api',
            'new_version': '6.2.0.Final'
        },
        
        # Other
        'org.jboss.logging:jboss-logging': {
            'new_version': '3.5.0.Final'
        },
        'org.wildfly.security:wildfly-elytron': {
            'new_version': '2.0.0.Final'
        },
        'com.sun.mail:javax.mail': {
            'new_artifact': 'jakarta.mail:jakarta.mail-api',
            'new_version': '2.1.0'
        },
        'javax.validation:validation-api': {
            'new_artifact': 'jakarta.validation:jakarta.validation-api',
            'new_version': '3.0.2'
        }
    })