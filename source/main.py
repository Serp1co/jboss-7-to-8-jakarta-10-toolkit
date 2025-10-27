#!/usr/bin/env python3
"""
Extensible migration framework for Java EE to Jakarta EE migrations.
Supports Java file namespace migrations and POM dependency migrations.
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from source.config_loader import ConfigurationLoader
from source.migration_engine import MigrationEngine
from source.models.migrator import MigrationConfig, MigrationType


def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format
    )
    
    # Reduce verbosity of some loggers
    if not verbose:
        logging.getLogger('source.migrators').setLevel(logging.WARNING)
    
    return logging.getLogger('MigrationFramework')


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Extensible migration framework for Java EE to Jakarta EE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Migration Types:
  java      - Migrate javax namespaces to jakarta in Java files
  pom       - Migrate POM dependencies from JBoss EAP 7 to EAP 8
  all       - Apply all migrations

Examples:
  # Dry run for all migrations
  python -m source.main /path/to/project --dry-run
  
  # Migrate only Java namespaces
  python -m source.main /path/to/project --type java
  
  # Migrate only POM dependencies
  python -m source.main /path/to/project --type pom
  
  # Use custom configuration
  python -m source.main /path/to/project --config config.json
  
  # Generate default configuration file
  python -m source.main --generate-config
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        nargs='?',
        help='The directory to process recursively'
    )
    parser.add_argument(
        '--type',
        choices=['java', 'pom', 'all'],
        default='all',
        help='Type of migration to perform (default: all)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='Generate a default configuration file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Don't actually modify files, just show what would be changed"
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help="Don't create backup files"
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show detailed information'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics only (implies --dry-run)'
    )
    
    return parser.parse_args()


def generate_config():
    """Generate default configuration file."""
    config_path = Path('migration_config.json')
    
    if config_path.exists():
        response = input(f"Configuration file '{config_path}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Configuration generation cancelled.")
            return False
    
    if ConfigurationLoader.save_default_config(config_path):
        print(f"✓ Generated default configuration: {config_path}")
        return True
    else:
        print(f"✗ Failed to generate configuration: {config_path}")
        return False


def load_configuration(config_path: Optional[str], logger: logging.Logger) -> MigrationConfig:
    """Load configuration from file or use defaults."""
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            config = ConfigurationLoader.load_from_file(config_file)
            logger.info(f"Loaded configuration from {config_file}")
        else:
            logger.warning(f"Configuration file {config_file} not found, using defaults")
            config = MigrationConfig()
    else:
        # Try to load from default location
        default_config = Path('config.json')
        if default_config.exists():
            config = ConfigurationLoader.load_from_file(default_config)
            logger.info(f"Loaded configuration from {default_config}")
        else:
            config = MigrationConfig()
            logger.debug("Using default configuration")
    
    return config


def print_summary(summary: Dict[str, Any], dry_run: bool):
    """Print migration summary."""
    print("-" * 60)
    print("Summary:")
    print(f"  Total files processed: {summary['total_files']}")
    print(f"  Files {'would be ' if dry_run else ''}modified: {summary['modified_files']}")
    print(f"  Total replacements: {summary['total_replacements']}")
    
    if summary['files_with_errors'] > 0:
        print(f"  ⚠ Files with errors: {summary['files_with_errors']}")
    
    if summary.get('by_type'):
        print("\n  By file type:")
        for ext, stats in sorted(summary['by_type'].items()):
            print(f"    {ext}: {stats['modified']}/{stats['count']} files, "
                  f"{stats['replacements']} replacements")
    
    # Show errors if any
    if summary.get('errors'):
        print("\n  Errors encountered:")
        for error_info in summary['errors'][:5]:  # Show first 5 errors
            print(f"    - {Path(error_info['file']).name}: {error_info['errors'][0]}")
        if len(summary['errors']) > 5:
            print(f"    ... and {len(summary['errors']) - 5} more errors")
    
    if dry_run:
        print("\nThis was a dry run. No files were actually modified.")
        print("Remove --dry-run flag to perform actual migration.")


def main():
    """Main entry point for the migration framework."""
    args = parse_arguments()
    
    # Handle config generation
    if args.generate_config:
        return 0 if generate_config() else 1
    
    # Validate directory argument
    if not args.directory:
        print("✗ Error: Directory argument is required unless using --generate-config")
        print("       Run with --help for usage information")
        return 1
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"✗ Error: Directory '{directory}' does not exist")
        return 1
    if not directory.is_dir():
        print(f"✗ Error: '{directory}' is not a directory")
        return 1
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Load configuration
    config = load_configuration(args.config, logger)
    
    # Override config with CLI arguments
    if args.dry_run or args.stats:
        config.dry_run = True
    if args.no_backup:
        config.backup = False
    if args.verbose:
        config.verbose = True
    
    # Determine migration types
    migration_types = set()
    if args.type == 'all':
        migration_types.add(MigrationType.ALL)
    elif args.type == 'java':
        migration_types.add(MigrationType.JAVA_NAMESPACE)
    elif args.type == 'pom':
        migration_types.add(MigrationType.POM_DEPENDENCY)
    
    # Create and run migration engine
    engine = MigrationEngine(config, logger)
    
    # Print header
    mode = "DRY RUN" if config.dry_run else "MIGRATION"
    print(f"\n{mode}: Processing directory: {directory.absolute()}")
    print(f"Migration types: {args.type}")
    print("-" * 60)
    
    try:
        summary = engine.migrate_directory(directory, migration_types)
        print_summary(summary, config.dry_run)
        
        # Return appropriate exit code
        if summary['files_with_errors'] > 0:
            return 2  # Partial success
        return 0  # Success
        
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())