# -*- coding: utf-8 -*-
"""
Migration script: Add structured error fields to tasks table

This migration adds error_code, error_message, and retryable fields
to provide structured error information for frontend.

Usage:
    python scripts/migrate_add_error_fields.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.database.session import session_scope
from src.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_add_error_fields():
    """Add structured error fields to tasks table"""
    
    with session_scope() as session:
        try:
            # Check if columns already exist
            result = session.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('tasks') WHERE name='error_code'"
            ))
            error_code_exists = result.scalar() > 0
            
            if error_code_exists:
                logger.info("Structured error fields already exist in tasks table")
                return
            
            # Add error_code column
            logger.info("Adding error_code column to tasks table...")
            session.execute(text(
                "ALTER TABLE tasks ADD COLUMN error_code TEXT"
            ))
            
            # Add error_message column
            logger.info("Adding error_message column to tasks table...")
            session.execute(text(
                "ALTER TABLE tasks ADD COLUMN error_message TEXT"
            ))
            
            # Rename old error_details to keep backward compatibility
            # (SQLite doesn't support renaming columns directly, so we keep both)
            
            # Add retryable column
            logger.info("Adding retryable column to tasks table...")
            session.execute(text(
                "ALTER TABLE tasks ADD COLUMN retryable INTEGER"  # SQLite uses INTEGER for BOOLEAN
            ))
            
            session.commit()
            logger.info("✓ Structured error fields added successfully")
            
            # Note: error_details column already exists, no need to add
            logger.info("✓ Keeping existing error_details column for backward compatibility")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    logger.info("Starting migration: Add structured error fields")
    migrate_add_error_fields()
    logger.info("Migration completed successfully")
