# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module that includes common code.

Code in this submodule is code that should be in something
like ska-pst-common.  It is duplicated here to avoid a
circular dependency between ska-pst-testutils and ska-pst-lmc.
"""

__all__ = [
    "calculate_dsp_subband_resources",
    "calculate_receive_common_resources",
    "calculate_receive_subband_resources",
    "calculate_receive_packet_resources",
    "calculate_smrb_subband_resources",
    "convert_value_to_quantity",
    "generate_data_key",
    "generate_dsp_scan_request",
    "generate_recv_scan_request",
    "generate_weights_key",
    "get_frequency_band_config",
    "get_udp_format_config",
    "ChangeEventSubscription",
    "DeviceProxyFactory",
    "PstDeviceProxy",
    "QuantityType",
    "TelescopeFacilityEnum",
]

from .band_config import get_frequency_band_config, get_udp_format_config
from .dsp_util import calculate_dsp_subband_resources, generate_dsp_scan_request
from .pst_device_proxy import ChangeEventSubscription, PstDeviceProxy, DeviceProxyFactory
from .quantity_helper import convert_value_to_quantity
from .receive_util import (
    calculate_receive_common_resources,
    calculate_receive_packet_resources,
    calculate_receive_subband_resources,
    generate_recv_scan_request,
)
from .smrb_util import (
    calculate_smrb_subband_resources,
    generate_data_key,
    generate_weights_key,
)
from .telescope_facility import TelescopeFacilityEnum
