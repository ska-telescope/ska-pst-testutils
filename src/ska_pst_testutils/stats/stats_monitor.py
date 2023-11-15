# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module to monitor statistics files."""

from __future__ import annotations

import logging
import pathlib
import threading
from dataclasses import InitVar, dataclass, field
from typing import List

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer


@dataclass(kw_only=True, frozen=True)
class StatFileCreatedEvent:
    """Data class capturing a file creation event.

    :ivar file_path: the full path to the file that was created.
    :vartype file_path: pathlib.Path
    :ivar create_datetime: the time, in seconds from epoch, when the file was created.
    :vartype create_datetime: float
    """

    file_path: pathlib.Path
    create_datetime: float


@dataclass(kw_only=True)
class StatFileEventDifference:
    """A data class used to calculate differences in file creation events.

    :ivar first_file_path: the path to the file that was created first
    :vartype first_file_path: pathlib.Path
    :ivar second_file_path: the path to the file that was created second
    :vartype second_file_path: pathlib.Path
    :ivar creation_time_difference: the difference in creation time of the files
    :vartype creation_time_difference: float
    """

    first_file_event: InitVar[StatFileCreatedEvent]
    second_file_event: InitVar[StatFileCreatedEvent]
    first_file_path: pathlib.Path = field(init=False)
    second_file_path: pathlib.Path = field(init=False)
    creation_time_difference: float = field(init=False)

    def __post_init__(
        self: StatFileEventDifference,
        first_file_event: StatFileCreatedEvent,
        second_file_event: StatFileCreatedEvent,
    ) -> None:
        """Set the computed properties for this instance."""
        self.first_file_path = first_file_event.file_path
        self.second_file_path = second_file_event.file_path
        self.creation_time_difference = second_file_event.create_datetime - first_file_event.create_datetime


class ScanStatFileWatcher(PatternMatchingEventHandler):
    """Class to watch for when STAT file files are created.

    Instances of this class watches a scan directory for real
    time monitoring STAT HDF5 files to be created and stores
    the events for later.
    """

    def __init__(
        self: ScanStatFileWatcher,
        scan_path: pathlib.Path,
        logger: logging.Logger | None = None,
    ) -> None:
        """Create instance of class.

        :param scan_path: the local scan path for files
        :type scan_path: pathlib.Path
        :param logger: the logger to use when performing logging, defaults to None
        :type logger: logging.Logger | None, optional
        """
        self._logger = logger or logging.getLogger(__name__)
        self._scan_path = scan_path
        self._events: List[StatFileCreatedEvent] = []
        self._observer = Observer()
        self._lock = threading.Lock()
        super().__init__(patterns=["*/monitoring_stats/*.h5"], ignore_directories=True, case_sensitive=True)

    def __del__(self: ScanStatFileWatcher) -> None:
        """Teardown the watcher safely when instance is destroyed."""
        self.stop()

    def watch(self: ScanStatFileWatcher) -> None:
        """Start watching for STAT files."""
        self._logger.debug("ScanStatFileWatcher starting to watch for file create events")
        with self._lock:
            assert not self._observer.is_alive(), "Watcher is already watching."
            self._observer.schedule(event_handler=self, path=self._scan_path, recursive=True)
            self._observer.start()

    def stop(self: ScanStatFileWatcher) -> None:
        """Stop watching for STAT files."""
        self._logger.debug("ScanStatFileWatcher stopping watching for file create events")
        with self._lock:
            if self._observer.is_alive():
                self._observer.stop()
            else:
                self._logger.warning("ScanStatFileWatcher is not currently watching")
            self._observer.join()

    def on_created(self: ScanStatFileWatcher, event: FileSystemEvent) -> None:
        """Handle an on created system event.

        The event comes from `watchdog` and this method converts the
        event to a :py:class:`StatFileCreatedEvent` instance and saves
        the event that can then later be retrieved from :py:attr:`events`.
        """
        file_path = pathlib.Path(event.src_path)
        file_event = StatFileCreatedEvent(
            file_path=file_path,
            create_datetime=file_path.stat().st_ctime,
        )
        self._logger.debug(f"Received on_created event {file_event}")

        with self._lock:
            self._events.append(file_event)

    @property
    def events(self: ScanStatFileWatcher) -> List[StatFileCreatedEvent]:
        """Get the list of file created events."""
        with self._lock:
            return [*self._events]

    def event_time_diffs(self: ScanStatFileWatcher) -> List[StatFileEventDifference]:
        """Get a list of differences between file creation events."""
        events = self.events
        if len(events) <= 1:
            return []

        return [
            StatFileEventDifference(first_file_event=f, second_file_event=s)
            for (f, s) in zip(events[:-1], events[1:])
        ]
