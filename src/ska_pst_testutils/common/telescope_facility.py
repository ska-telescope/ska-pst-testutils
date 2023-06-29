# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST LMC project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module containing enum that presents the different telescope facilities (i.e. Mid vs Low).

This has been copied verbatim from ska-pst-lmc to break a circular dependency.
When code is put is a `ska-pst-common` python project then this should be
migrated there.
"""

import enum


class TelescopeFacilityEnum(enum.IntEnum):
    """Enum representing the different telescope facilities within SKAO."""

    Low = 1
    """Used to present that the functionality is for the SKA-Low facility."""

    Mid = 2
    """Used to present that the functionality is for the SKA-Mid facility."""
