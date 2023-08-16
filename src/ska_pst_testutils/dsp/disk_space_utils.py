# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module class to handle disk space.

This module provides the `DiskSpaceUtil` class to work with the
disk space used by DSP.DISK and a simple dataclass, `DiskUsage`
that can be used to get the current disk usage stats.
"""

from __future__ import annotations

import dataclasses
import logging
import math
import os
import pathlib
import shutil
from types import TracebackType
from typing import List

KILOBYTES = 1024


@dataclasses.dataclass(kw_only=True)
class DiskUsage:
    """Data class exposing the disk usages of a mount.

    All values are in bytes.
    """

    total: int
    free: int
    used: int


class DiskSpaceUtil:
    """Utility class for dealing with disk space during tests.

    This class provides a wrapper for the current disk usage but
    also has the ability to fill the disk with files to consume
    a certain amount of space.

    This can be used as a context manager to allow for cleanup
    of files even if there is an exception.
    """

    def __init__(self: DiskSpaceUtil, dsp_mount: str, logger: logging.Logger | None = None) -> None:
        """Initialise the instance."""
        self.dsp_mount = pathlib.Path(dsp_mount)
        self.logger = logger or logging.getLogger(__name__)
        self._files: List[pathlib.Path] = list()

    def __enter__(self: DiskSpaceUtil) -> DiskSpaceUtil:
        """Start a context using this instance."""
        return self

    def __exit__(
        self: DiskSpaceUtil,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Cleanup context."""
        self.cleanup()

    def cleanup(self: DiskSpaceUtil) -> None:
        """Clean up any files that may have been written by this instance."""
        for f in self._files:
            try:
                self.logger.info(f"Removing file {f}")
                f.unlink(missing_ok=True)
            except Exception:
                self.logger.exception(f"Error in deleting file {f}", exc_info=True)

        self._files.clear()

    def curr_disk_space(self: DiskSpaceUtil) -> DiskUsage:
        """Get current disk space."""
        disk_usage = shutil.disk_usage(self.dsp_mount)

        return DiskUsage(total=disk_usage.total, free=disk_usage.free, used=disk_usage.used)

    def create_tmp_file(self: DiskSpaceUtil, fill_bytes: int) -> None:
        """Create a temporary file on the mount."""
        self.logger.info(f"Creating tmp file with at least {fill_bytes} bytes")

        num_blocks_kb = int(math.ceil(float(fill_bytes) / KILOBYTES))
        output_file = self.dsp_mount / "zero.txt"

        cmd = f"dd if=/dev/zero of={str(output_file.absolute())} count={num_blocks_kb} bs={KILOBYTES}"
        self.logger.info(f"Creating file: {output_file}")
        try:
            err_code = os.system(cmd)
            if err_code != 0:
                raise RuntimeError(f"Error in running '{cmd}'. Error code = {err_code}")
            self._files.append(output_file)
            self.logger.info(f"Created tmp file: {output_file}")
        except Exception:
            self.logger.exception(
                f"Error in trying to generate file with {fill_bytes} bytes",
                exc_info=True,
            )
            try:
                if output_file.exists():
                    output_file.unlink()
            except Exception:
                self.logger.warning("Error when trying to delete file.", exc_info=True)
