#!/usr/bin/env python3
"""
Extensible migration framework for Java EE to Jakarta EE migrations.
Supports Java file namespace migrations and POM dependency migrations.
"""
import logging
import argparse
from pathlib import Path

from source.config_loader import ConfigurationLoader
from source.migration_engine import MigrationEngine
from source.models.migrator import MigrationConfig, MigrationType

def setup_logging(verbose: bool) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('MigrationFramework')


def main():
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
  python migrate.py /path/to/project --dry-run
  
  # Migrate only Java namespaces
  python migrate.py /path/to/project --type java
  
  # Migrate only POM dependencies
  python migrate.py /path/to/project --type pom
  
  # Use custom configuration
  python migrate.py /path/to/project --config config.json
  
  # Generate default configuration file
  python migrate.py --generate-config
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
        help='Type of migration to perform'
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
    
    args = parser.parse_args()
    
    # Handle config generation
    if args.generate_config:
        config_path = Path('migration_config.json')
        ConfigurationLoader.save_default_config(config_path)
        print(f"Generated default configuration: {config_path}")
        return 0
    
    # Validate directory argument
    if not args.directory:
        parser.error("Directory argument is required unless using --generate-config")
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return 1
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory")
        return 1
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Load configuration
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            config = ConfigurationLoader.load_from_file(config_path)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.warning(f"Configuration file {config_path} not found, using defaults")
            config = MigrationConfig()
    else:
        config = MigrationConfig()
    
    # Override config with CLI arguments
    if args.dry_run:
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
    
    print(f"{'DRY RUN: ' if config.dry_run else ''}Processing directory: {directory.absolute()}")
    print(f"Migration types: {args.type}")
    print("-" * 60)
    
    summary = engine.migrate_directory(directory, migration_types)
    
    # Print summary
    print("-" * 60)
    print("Summary:")
    print(f"  Total files processed: {summary['total_files']}")
    print(f"  Files {'would be ' if config.dry_run else ''}modified: {summary['modified_files']}")
    print(f"  Total replacements: {summary['total_replacements']}")
    
    if summary['files_with_errors'] > 0:
        print(f"  Files with errors: {summary['files_with_errors']}")
    
    if summary['by_type']:
        print("\n  By file type:")
        for ext, stats in summary['by_type'].items():
            print(f"    {ext}: {stats['modified']}/{stats['count']} files, {stats['replacements']} replacements")
    
    if config.dry_run:
        print("\nThis was a dry run. No files were actually modified.")
        print("Remove --dry-run flag to perform actual migration.")
    
    return 0


if __name__ == "__main__":
    exit(main())