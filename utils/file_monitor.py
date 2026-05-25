"""File monitoring service using watchdog for real-time file change detection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events and triggers callbacks."""

    def __init__(self, callback: Callable[[str], None], file_pattern: Optional[str] = None):
        """
        Initialize the file change handler.

        Args:
            callback: Function to call when file changes
            file_pattern: Optional pattern to match (e.g., "*.csv", "*.json")
        """
        self.callback = callback
        self.file_pattern = file_pattern

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path
        if self.file_pattern:
            if not Path(file_path).name.endswith(self.file_pattern.replace("*", "")):
                return

        logger.info(f"File modified: {file_path}")
        try:
            self.callback(file_path)
        except Exception as e:
            logger.error(f"Error in file change callback: {e}")


class FileMonitor:
    """Monitors file system for changes using watchdog."""

    def __init__(self):
        """Initialize the file monitor."""
        self.observer: Optional[Observer] = None
        self.watch_handlers: dict = {}

    def start(self) -> None:
        """Start the file monitor."""
        if self.observer is None:
            self.observer = Observer()
            self.observer.start()
            logger.info("File monitor started")

    def stop(self) -> None:
        """Stop the file monitor."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("File monitor stopped")

    def watch_directory(
        self,
        directory: str,
        callback: Callable[[str], None],
        file_pattern: Optional[str] = None,
        watch_id: Optional[str] = None,
    ) -> str:
        """
        Watch a directory for file changes.

        Args:
            directory: Directory path to watch
            callback: Function to call on file changes
            file_pattern: Optional pattern to match
            watch_id: Optional ID for this watch

        Returns:
            Watch ID for later removal
        """
        if self.observer is None:
            self.start()

        watch_id = watch_id or f"watch_{len(self.watch_handlers)}"
        handler = FileChangeHandler(callback, file_pattern)
        watch = self.observer.schedule(handler, directory, recursive=True)
        self.watch_handlers[watch_id] = (watch, directory)
        logger.info(f"Watching directory: {directory} (ID: {watch_id})")
        return watch_id

    def unwatch_directory(self, watch_id: str) -> None:
        """Stop watching a directory."""
        if watch_id in self.watch_handlers:
            watch, directory = self.watch_handlers.pop(watch_id)
            self.observer.unschedule(watch)
            logger.info(f"Stopped watching: {directory} (ID: {watch_id})")

    def watch_file(
        self,
        file_path: str,
        callback: Callable[[str], None],
        watch_id: Optional[str] = None,
    ) -> str:
        """
        Watch a specific file for changes.

        Args:
            file_path: File path to watch
            callback: Function to call on file changes
            watch_id: Optional ID for this watch

        Returns:
            Watch ID for later removal
        """
        file_obj = Path(file_path)
        directory = str(file_obj.parent)
        file_name = file_obj.name

        def file_specific_callback(changed_file: str) -> None:
            if Path(changed_file).name == file_name:
                callback(changed_file)

        return self.watch_directory(directory, file_specific_callback, watch_id=watch_id)


# Global file monitor instance
_file_monitor: Optional[FileMonitor] = None


def get_file_monitor() -> FileMonitor:
    """Get or create the global file monitor instance."""
    global _file_monitor
    if _file_monitor is None:
        _file_monitor = FileMonitor()
    return _file_monitor


def watch_csv_files(directory: str, callback: Callable[[str], None]) -> str:
    """
    Convenience function to watch CSV files in a directory.

    Args:
        directory: Directory to watch
        callback: Function to call when CSV files change

    Returns:
        Watch ID
    """
    monitor = get_file_monitor()
    monitor.start()
    return monitor.watch_directory(directory, callback, file_pattern="*.csv")


def watch_json_files(directory: str, callback: Callable[[str], None]) -> str:
    """
    Convenience function to watch JSON files in a directory.

    Args:
        directory: Directory to watch
        callback: Function to call when JSON files change

    Returns:
        Watch ID
    """
    monitor = get_file_monitor()
    monitor.start()
    return monitor.watch_directory(directory, callback, file_pattern="*.json")


def stop_monitoring() -> None:
    """Stop all file monitoring."""
    global _file_monitor
    if _file_monitor is not None:
        _file_monitor.stop()
        _file_monitor = None
        logger.info("All monitoring stopped")
