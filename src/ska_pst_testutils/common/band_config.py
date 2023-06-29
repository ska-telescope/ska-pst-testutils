# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module provides configuration for the different frequency bands.

This has been copied verbatim from ska-pst-lmc to break a circular dependency.
When code is put is a `ska-pst-common` python project then this should be
migrated there.
"""

__all__ = ["get_frequency_band_config", "get_udp_format_config"]

from typing import Any, Dict, Optional

LOW_BAND_CONFIG = {
    "udp_format": "LowPST",
    "packet_nchan": 24,
    "packet_nsamp": 32,
    "packets_per_buffer": 16,
    "num_of_buffers": 64,
}

COMMON_MID_CONFIG = {
    "packet_nchan": 185,
    "packet_nsamp": 4,
}

MID_BAND_CONFIG = {
    "1": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand1",
        "packets_per_buffer": 1024,
        "num_of_buffers": 128,
    },
    "2": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand2",
        "packets_per_buffer": 1024,
        "num_of_buffers": 128,
    },
    "3": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand3",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
    "4": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand4",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
    "5a": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand5",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
    "5b": {
        **COMMON_MID_CONFIG,
        "udp_format": "MidPSTBand5",
        "packets_per_buffer": 512,
        "num_of_buffers": 256,
    },
}

# this inverts the frequency band configs to being a UDP format config
# Band 5a and 5b have the same udp_format
UDP_FORMAT_CONFIG = {
    "LowPST": LOW_BAND_CONFIG,
    **{
        config["udp_format"]: config
        for (freq_band,config) in MID_BAND_CONFIG.items() if freq_band != "5b"
    }
}

def get_frequency_band_config(frequency_band: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
    """Get the configuration specific for a frequency band.

    This will return the configuration that is specific to a frequency band.
    The standard for SKA is that if the frequency_band is only set or is "low"
    then it corresponds to the Low telescope, which has only one band. Frequency
    bands of 1, 2, 3, 4, 5a, or 5b will return specific configuration.

    The keys that are returned are:
        * udp_format
        * packet_nchan
        * packet_nsamp
        * packets_per_buffer
        * num_of_buffers

    An example output is as follows::

        {
            "udp_format": "LowPST",
            "packet_nchan": 24,
            "packet_nsamp": 32,
            "packets_per_buffer": 16,
            "num_of_buffers": 64,
        }

    :param frequency_band: the frequency band to get configuration for, defaults to None
    :type frequency_band: Optional[str], optional
    :return: a dictionary of configuration for the frequency band.
    :rtype: Dict[str, Any]
    """
    if frequency_band is None or frequency_band == "low":
        return LOW_BAND_CONFIG

    return MID_BAND_CONFIG[frequency_band]

def get_udp_format_config(udp_format: str) -> dict:
    """Get the UDP format configuration.

    This will assert that the udp_format is valid.

    This will return the configuration that is specific to a UDP format.
    This is related to the frequency band config returned by
    :py:func:`get_frequency_band_config` but uses the UDP format
    as a key not the frequency band.

    The keys that are returned are:
        * udp_format
        * packet_nchan
        * packet_nsamp
        * packets_per_buffer
        * num_of_buffers

    An example output is as follows::

        {
            "udp_format": "LowPST",
            "packet_nchan": 24,
            "packet_nsamp": 32,
            "packets_per_buffer": 16,
            "num_of_buffers": 64,
        }

    :param udp_format: the UDP formate to get configuration for
    :type udp_format: str
    :return: a dictionary of configuration for the UDP format.
    :rtype: Dict[str, Any]
    """
    assert udp_format in UDP_FORMAT_CONFIG, (
        f"expected {udp_format} to be in the UDP_FORMAT_CONFIG. Valid keys are {UDP_FORMAT_CONFIG.keys()}"
    )
    return UDP_FORMAT_CONFIG[udp_format]
