# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Submodule for working with DSP, such as working with the disk space."""

__all__ = [
    "DiskUsage",
    "DiskSpaceUtil",
]

from .disk_space_utils import DiskSpaceUtil, DiskUsage
