from __future__ import annotations

from pathlib import Path
from typing import Iterable, Callable, Any
from datetime import datetime, timezone, timedelta

import logging

from sqlalchemy import select, func

from src.storage.database import Capture, Event # Import necessary models and initializer

logger = logging.getLogger(__name__)


def cleanup_old_files(session_factory: Callable[..., Any], directories: Iterable[str | Path], max_age_days: int) -> int:
    """
    Marks old Capture and Event records as deleted in the database and removes corresponding files.
    """
    now_utc = datetime.now(timezone.utc)
    cutoff_date = now_utc - timedelta(days=max_age_days)
    removed_count = 0

    with session_factory() as session:
        try:
            # Mark old Capture records as deleted
            captures_to_delete = session.execute(
                select(Capture).filter(Capture.timestamp < cutoff_date, Capture.deleted == False)
            ).scalars().all()

            for capture in captures_to_delete:
                capture.deleted = True
                removed_count += 1
                logger.debug(f"Marked old capture {capture.file_path} as deleted.")
            
            # Mark old Event records as deleted
            events_to_delete = session.execute(
                select(Event).filter(Event.timestamp < cutoff_date, Event.deleted == False)
            ).scalars().all()

            for event in events_to_delete:
                event.deleted = True
                removed_count += 1
                logger.debug(f"Marked old event {event.id} as deleted.")

            session.commit()
            logger.info(f"Marked {removed_count} old records as deleted in DB.")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark old records as deleted: {e}")
    
    # Also clean up physical files that are older than max_age_days, regardless of DB status
    # This acts as a failsafe for files not linked to DB records or if DB cleanup fails
    physical_removed_count = 0
    for d in directories:
        for p in Path(d).glob("**/*"):
            if p.is_file():
                try:
                    file_mtime_utc = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                    if file_mtime_utc < cutoff_date:
                        p.unlink()
                        physical_removed_count += 1
                        logger.debug(f"Physically deleted old file: {p}")
                except Exception as e:
                    logger.debug(f"Failed to physically remove old file {p}: {e}")
    
    if physical_removed_count > 0:
        logger.info(f"Physically deleted {physical_removed_count} old files from disk.")

    return removed_count + physical_removed_count


def cleanup_size_limit(session_factory: Callable[..., Any], directory: str | Path, max_bytes: int) -> int:
    """
    Marks Capture and Event records as deleted in the database and removes corresponding files
    if the total storage size exceeds max_bytes. Prioritizes oldest records.
    """
    removed_count = 0
    with session_factory() as session:
        try:
            # Get current total size of non-deleted captures and events
            total_capture_size = session.execute(
                select(func.sum(Capture.size_bytes)).filter(Capture.deleted == False)
            ).scalar_one_or_none() or 0

            # For simplicity, we'll only consider Capture sizes for the limit for now.
            # Events are typically small and don't contribute significantly to storage.
            current_total_bytes = total_capture_size
            
            if current_total_bytes <= max_bytes:
                logger.info(f"Current storage ({current_total_bytes} bytes) is within limit ({max_bytes} bytes). No size cleanup needed.")
                return 0

            logger.info(f"Storage ({current_total_bytes} bytes) exceeds limit ({max_bytes} bytes). Initiating size cleanup.")

            # Fetch oldest non-deleted captures, ordered by timestamp
            captures_to_consider = session.execute(
                select(Capture).filter(Capture.deleted == False).order_by(Capture.timestamp.asc())
            ).scalars().all()

            for capture in captures_to_consider:
                if current_total_bytes <= max_bytes:
                    break # Stop if we're within limits
                
                capture.deleted = True
                current_total_bytes -= capture.size_bytes
                removed_count += 1
                logger.debug(f"Marked capture {capture.file_path} as deleted due to size limit.")
            
            session.commit()
            logger.info(f"Marked {removed_count} records as deleted due to size limit.")

            # Collect file paths of captures that were just marked for deletion
            files_to_physically_delete = [Path(c.file_path) for c in captures_to_consider if c.deleted]

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to mark records as deleted due to size limit: {e}")
            return 0 # Return 0 if DB operation failed

    physical_removed_count = 0
    for file_path in files_to_physically_delete:
        if file_path.exists():
            try:
                file_path.unlink()
                physical_removed_count += 1
                logger.debug(f"Physically deleted file {file_path} associated with deleted capture record due to size limit.")
            except Exception as e:
                logger.error(f"Failed to physically remove file {file_path} for deleted capture due to size limit: {e}")

    if physical_removed_count > 0:
        logger.info(f"Physically deleted {physical_removed_count} files from disk associated with deleted records due to size limit.")

    return removed_count


def physical_cleanup_deleted_records(session_factory: Callable[..., Any], retention_days: int) -> int:
    """
    Permanently deletes records and their associated files that have been marked as deleted
    and exceed the retention period.
    """
    now_utc = datetime.now(timezone.utc)
    retention_cutoff = now_utc - timedelta(days=retention_days)
    hard_deleted_count = 0

    with session_factory() as session:
        try:
            # Find Capture records marked as deleted and older than retention_cutoff
            captures_to_hard_delete = session.execute(
                select(Capture).filter(Capture.deleted == True, Capture.timestamp < retention_cutoff)
            ).scalars().all()

            for capture in captures_to_hard_delete:
                try:
                    file_path = Path(capture.file_path)
                    if file_path.exists():
                        file_path.unlink()
                        logger.debug(f"Physically deleted retained file: {file_path}")
                    session.delete(capture)
                    hard_deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to hard delete capture {capture.file_path} or its file: {e}")
            
            # Find Event records marked as deleted and older than retention_cutoff
            events_to_hard_delete = session.execute(
                select(Event).filter(Event.deleted == True, Event.timestamp < retention_cutoff)
            ).scalars().all()

            for event in events_to_hard_delete:
                try:
                    # Events might not have associated files, or their files are managed differently
                    # For now, just delete the record.
                    session.delete(event)
                    hard_deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to hard delete event {event.id}: {e}")

            session.commit()
            logger.info(f"Hard deleted {hard_deleted_count} records and their files older than {retention_days} days.")

        except Exception as e:
            session.rollback()
            logger.error(f"Error during physical cleanup of deleted records: {e}")
    
    return hard_deleted_count


