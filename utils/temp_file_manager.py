"""
Temporary file management utility for Docker containers
"""
import os
import tempfile
import shutil
import logging
import atexit
import threading
import time
from typing import Optional, List
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TempFileManager:
    """Manages temporary files with automatic cleanup"""
    
    def __init__(self, temp_dir: Optional[str] = None, max_age_hours: int = 24):
        """
        Initialize temporary file manager
        
        Args:
            temp_dir: Custom temporary directory path
            max_age_hours: Maximum age of temporary files before cleanup
        """
        self.temp_dir = temp_dir or os.getenv('TEMP_DIR', '/app/temp')
        self.max_age_hours = max_age_hours
        self.created_files: List[str] = []
        self.lock = threading.Lock()
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
        
        # Start background cleanup thread
        self._start_cleanup_thread()
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'grading_', dir: Optional[str] = None) -> str:
        """
        Create a temporary file
        
        Args:
            suffix: File suffix (e.g., '.pdf', '.docx')
            prefix: File prefix
            dir: Directory to create file in (defaults to self.temp_dir)
            
        Returns:
            Path to created temporary file
        """
        temp_dir = dir or self.temp_dir
        
        # Create temporary file
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=temp_dir
        )
        os.close(fd)  # Close file descriptor, we just need the path
        
        # Track created file
        with self.lock:
            self.created_files.append(temp_path)
        
        logger.debug(f"Created temporary file: {temp_path}")
        return temp_path
    
    def create_temp_dir(self, prefix: str = 'grading_dir_', dir: Optional[str] = None) -> str:
        """
        Create a temporary directory
        
        Args:
            prefix: Directory prefix
            dir: Parent directory (defaults to self.temp_dir)
            
        Returns:
            Path to created temporary directory
        """
        temp_dir = dir or self.temp_dir
        
        temp_path = tempfile.mkdtemp(
            prefix=prefix,
            dir=temp_dir
        )
        
        # Track created directory
        with self.lock:
            self.created_files.append(temp_path)
        
        logger.debug(f"Created temporary directory: {temp_path}")
        return temp_path
    
    @contextmanager
    def temp_file(self, suffix: str = '', prefix: str = 'grading_'):
        """
        Context manager for temporary files
        
        Args:
            suffix: File suffix
            prefix: File prefix
            
        Yields:
            Path to temporary file
        """
        temp_path = self.create_temp_file(suffix=suffix, prefix=prefix)
        try:
            yield temp_path
        finally:
            self.cleanup_file(temp_path)
    
    @contextmanager
    def temp_dir(self, prefix: str = 'grading_dir_'):
        """
        Context manager for temporary directories
        
        Args:
            prefix: Directory prefix
            
        Yields:
            Path to temporary directory
        """
        temp_path = self.create_temp_dir(prefix=prefix)
        try:
            yield temp_path
        finally:
            self.cleanup_file(temp_path)
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Clean up a specific file or directory
        
        Args:
            file_path: Path to file or directory to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                # Remove from tracking list
                with self.lock:
                    if file_path in self.created_files:
                        self.created_files.remove(file_path)
                
                logger.debug(f"Cleaned up temporary file: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup {file_path}: {e}")
            return False
        
        return True
    
    def cleanup_all(self):
        """Clean up all tracked temporary files"""
        with self.lock:
            files_to_cleanup = self.created_files.copy()
        
        for file_path in files_to_cleanup:
            self.cleanup_file(file_path)
        
        logger.info(f"Cleaned up {len(files_to_cleanup)} temporary files")
    
    def cleanup_old_files(self):
        """Clean up old temporary files based on age"""
        if not os.path.exists(self.temp_dir):
            return
        
        current_time = time.time()
        max_age_seconds = self.max_age_hours * 3600
        cleaned_count = 0
        
        try:
            for root, dirs, files in os.walk(self.temp_dir):
                # Clean up files
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.debug(f"Cleaned up old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup old file {file_path}: {e}")
                
                # Clean up empty directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # Directory is empty
                            dir_age = current_time - os.path.getmtime(dir_path)
                            if dir_age > max_age_seconds:
                                os.rmdir(dir_path)
                                cleaned_count += 1
                                logger.debug(f"Cleaned up old directory: {dir_path}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup old directory {dir_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error during old files cleanup: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old temporary files/directories")
    
    def get_temp_usage(self) -> dict:
        """
        Get temporary directory usage statistics
        
        Returns:
            Dictionary with usage statistics
        """
        if not os.path.exists(self.temp_dir):
            return {"total_size": 0, "file_count": 0, "dir_count": 0}
        
        total_size = 0
        file_count = 0
        dir_count = 0
        
        try:
            for root, dirs, files in os.walk(self.temp_dir):
                dir_count += len(dirs)
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except Exception:
                        pass  # Skip files we can't access
        except Exception as e:
            logger.error(f"Error calculating temp usage: {e}")
        
        return {
            "total_size": total_size,
            "file_count": file_count,
            "dir_count": dir_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def _start_cleanup_thread(self):
        """Start background thread for periodic cleanup"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    self.cleanup_old_files()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Started background cleanup thread")

# Global instance
temp_manager = TempFileManager()

# Convenience functions
def create_temp_file(suffix: str = '', prefix: str = 'grading_') -> str:
    """Create a temporary file"""
    return temp_manager.create_temp_file(suffix=suffix, prefix=prefix)

def create_temp_dir(prefix: str = 'grading_dir_') -> str:
    """Create a temporary directory"""
    return temp_manager.create_temp_dir(prefix=prefix)

def cleanup_file(file_path: str) -> bool:
    """Clean up a specific file"""
    return temp_manager.cleanup_file(file_path)

def get_temp_usage() -> dict:
    """Get temporary directory usage statistics"""
    return temp_manager.get_temp_usage()

# Context managers
temp_file = temp_manager.temp_file
temp_dir = temp_manager.temp_dir