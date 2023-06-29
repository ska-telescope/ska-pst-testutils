# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module to provide helper method to convert quantities with units to a value"""

__all__ = [
    "convert_value_to_quantity",
    "QuantityType"
]

import re
from typing import TypeAlias

import astropy.units as u

# add unit aliases that may arise in our tests, including using British spelling of metre.
u.add_enabled_aliases(
    {
        # add English spelling for metre
        "metre": u.m,
        "metres": u.m,
        # add second abbreviations
        "seconds": u.s,
        "sec": u.s,
        "secs": u.s,
        # minutes
        "minutes": u.min,
        "mins": u.min,
        # add hours
        "hours": u.h,
        # add milliseconds
        "milliseconds": u.ms,
    }
)

QuantityType: TypeAlias = str | u.Quantity
QUANTITY_REGEX = r"^(?:[1-9]\d*|0)?(?:\.\d+)?(?:\s+\w+)?$"


def convert_value_to_quantity(value: str) -> QuantityType:
    """Convert a value string to a quantity.

    This tries to use the astropy.units package to see
    if it can convert it to a quantity.  If the value starts
    with a number then it is expected to be a quantity (value
    with optional unit). If it isn't a number the string value
    is returned.

    This is method should be extended to handled the edge cases
    that may arise in the future.
    """
    if re.match(QUANTITY_REGEX, value) is not None:
        return u.Quantity(value)
    else:
        return value
