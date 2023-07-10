# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for having a scan id utility class."""

from __future__ import annotations

__all__ = [
    "ScanIdFactory",
]

from random import randint
from typing import Set

MIN_SCAN_ID: int = 10
MAX_SCAN_ID: int = 1000


class ScanIdFactory:
    """Utility class to generate random scan ids that are unique upon each call.

    Instanaces of this class should be at a session level scope rather than
    being created for every scan.  This will allow it to keep track of previously
    generated scan ids.
    """

    def __init__(self: ScanIdFactory) -> None:
        """Initialise the factory."""
        self._previous_scan_ids: Set[int] = set()

    def generate_scan_id(self: ScanIdFactory) -> int:
        """Generate next scan id."""
        next_scan_id = randint(MIN_SCAN_ID, MAX_SCAN_ID)
        while next_scan_id in self._previous_scan_ids:
            next_scan_id = randint(MIN_SCAN_ID, MAX_SCAN_ID)

        self._previous_scan_ids.add(next_scan_id)
        return next_scan_id
