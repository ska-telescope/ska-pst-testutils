# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Submodule for UDP generator classes.

This package provides Python classes for generating
UDP packet streams. These classes should only be used
where there is no upstream UDP data being sent to the PST
system under test.
"""

__all__ = [
    "UdpDataGenerator",
]

from .udp_data_generator import UdpDataGenerator
