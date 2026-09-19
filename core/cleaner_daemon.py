"""
Garbage collector daemon for temporary video storage.
Prevents VPS disk exhaustion by auto-purging old files.
"""

import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CleanerDaemon")

def cleanup_old_files(directories: list, max_age_seconds: int = 3600):
    """
    Deletes files older than max_age_seconds in given directories.
    """
    now = time.time()
    deleted_count = 0
    reclaimed_bytes = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                try:
                    file_age = now - os.path.getmtime(filepath)
                    if file_age > max_age_seconds:
                        size = os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_count += 1
                        reclaimed_bytes += size
                except Exception as e:
                    logger.error(f"Failed to delete {filepath}: {e}")
                    
    if deleted_count > 0:
        mb = reclaimed_bytes / (1024 * 1024)
        logger.info(f"Auto-purge complete: Removed {deleted_count} files ({mb:.2f} MB freed).")

if __name__ == "__main__":
    import sys
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dirs = [
        os.path.join(base, "storage", "inputs"),
        os.path.join(base, "storage", "outputs"),
        os.path.join(base, "storage", "temp")
    ]
    logger.info("Starting storage garbage cleaner daemon...")
    while True:
        cleanup_old_files(dirs, max_age_seconds=3600)
        time.sleep(300) # Check every 5 minutes
