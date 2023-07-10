# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for handling PST Observation Mode."""

from __future__ import annotations

import enum


class PstObservationMode(enum.Enum):
    """An enumeration for handling different PST observation modes.

    This enum is used to provide logic around a given observation mode,
    including ability to get the CSP Json config example string given
    the current observation mode.
    """

    PULSAR_TIMING = "PULSAR_TIMING"
    DYNAMIC_SPECTRUM = "DYNAMIC_SPECTRUM"
    FLOW_THROUGH = "FLOW_THROUGH"
    VOLTAGE_RECORDER = "VOLTAGE_RECORDER"

    @staticmethod
    def from_str(value: str) -> PstObservationMode:
        """Get observation mode from a string.

        This is an extension to the Python enum because the
        PST BDD tests may use 'voltage recorder' or 'pulsar timing'.
        This will capitalise the string and replace spaces with
        underscores to then try to get the enum value.
        """
        return PstObservationMode[value.upper().replace(" ", "_")]

    def csp_scan_example_str(self: PstObservationMode) -> str:
        """Get CSP Scan example string.

        This is to be used when calling the
        :py:meth:`ska_telmodel.csp.get_csp_config_example` method
        to retreive the correct example CSP JSON data.
        """
        if self == PstObservationMode.PULSAR_TIMING:
            suffix = "pt"
        elif self == PstObservationMode.DYNAMIC_SPECTRUM:
            suffix = "ds"
        elif self == PstObservationMode.FLOW_THROUGH:
            suffix = "ft"
        else:
            suffix = "vr"

        return f"pst_scan_{suffix}"
