# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module containing enum that presents the different telescope facilities (i.e. Mid vs Low).

This has been copied verbatim from ska-pst-lmc to break a circular dependency.
When code is put is a `ska-pst-common` python project then this should be
migrated there.
"""

from __future__ import annotations

import enum


class TelescopeFacilityEnum(enum.IntEnum):
    """Enum representing the different telescope facilities within SKAO."""

    Low = 1
    """Used to present that the functionality is for the SKA-Low facility."""

    Mid = 2
    """Used to present that the functionality is for the SKA-Mid facility."""

    @property
    def telescope(self: TelescopeFacilityEnum) -> str:
        """Get the SKA telescope tha the facility enum represents."""
        return f"SKA{self.name}"

    @staticmethod
    def from_telescope(telescope: str) -> TelescopeFacilityEnum:
        """Get enum value based on telescope string.

        The `telescope` parameter must be either "SKALow" or "SKAMid".
        """
        assert telescope.startswith("SKA")
        facility_str = telescope[3:]

        return TelescopeFacilityEnum[facility_str]
