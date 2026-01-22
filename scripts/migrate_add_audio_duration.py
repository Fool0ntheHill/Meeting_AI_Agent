# -*- coding: utf-8 -*-
"""
Migration script: Add audio_duration column to tasks table

This migration adds the audio_duration column to store audio duration
at task creation time (from upload response), making it available
from progress=0 for accurate ETA calculation.

Usage:
    python scripts/migrate_add_audio_duration.py
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


def migrate_add_audio_duration():
    """Add audio_duration column to tasks table"""
    
    with session_scope() as session:
        try:
            # Check if column already exists
            result = session.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('tasks') WHERE name='audio_duration'"
            ))
            column_exists = result.scalar() > 0
            
            if column_exists:
                logger.info("Column 'audio_duration' already exists in tasks table")
                return
            
            # Add audio_duration column
            logger.info("Adding audio_duration column to tasks table...")
            session.execute(text(
                "ALTER TABLE tasks ADD COLUMN audio_duration REAL"
            ))
            session.commit()
            logger.info("✓ Column 'audio_duration' added successfully")
            
            # Backfill audio_duration from transcript records for existing tasks
            logger.info("Backfilling audio_duration from transcript records...")
            result = session.execute(text("""
                UPDATE tasks
                SET audio_duration = (
                    SELECT duration
                    FROM transcripts
                    WHERE transcripts.task_id = tasks.task_id
                    LIMIT 1
                )
                WHERE audio_duration IS NULL
                AND EXISTS (
                    SELECT 1 FROM transcripts WHERE transcripts.task_id = tasks.task_id
                )
            """))
            session.commit()
            updated_count = result.rowcount
            logger.info(f"✓ Backfilled audio_duration for {updated_count} existing tasks")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


if __name__ == "__main__":
    logger.info("Starting migration: Add audio_duration column")
    migrate_add_audio_duration()
    logger.info("Migration completed successfully")
