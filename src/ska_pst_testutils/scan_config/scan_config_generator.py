# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module used to generator scan configurations."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from ska_pst_testutils.common import (
    TelescopeFacilityEnum,
    calculate_receive_subband_resources,
    calculate_smrb_subband_resources,
    generate_recv_scan_request,
    get_frequency_band_config,
)


def calculate_resolution(udp_format: str, nchan: int, ndim: int, npol: int, nbits: int, **kwargs: Any) -> int:
    """Calculate resolution of UDP data."""
    if udp_format == "LowPST":
        nsamp_per_packet = 32
    else:
        nsamp_per_packet = 185

    return nsamp_per_packet * nchan * ndim * npol * nbits // 8


class ScanConfigGenerator:
    """Utility class to generate Scan configuraiton."""

    def __init__(
        self: ScanConfigGenerator,
        beam_id: int,
        telescope: str,
        facility: TelescopeFacilityEnum,
        frequency_band: str,
        max_scan_length: float = 10.0,
    ) -> None:
        """Create instance of ScanConfigGenerator.

        :param beam_id: the ID of the beam being used to generate config for.
        :param telescope: the Telescope for which the config is being generated for.
        :param facility: the facility that config is being generated for.
        :type facility: TelescopeFacilityEnum.
        :param frequency_band: the frequency band that the configuration is for.
        :param max_scan_length: the maximum scan length, default is 10 seconds.
        """
        self._beam_id = beam_id
        self._telescope = telescope
        self._facility = facility
        if facility == TelescopeFacilityEnum.Low:
            self._frequency_band = "low"
        else:
            self._frequency_band = frequency_band
        self._previous_config_ids: List[str] = []
        self._current_config: Dict[str, Any] = {}
        self._max_scan_length = max_scan_length
        self._observation_mode: Optional[str] = None
        self._config_override: Dict[str, Any] = {}

    @property
    def facility(self: ScanConfigGenerator) -> TelescopeFacilityEnum:
        """Get the current facility."""
        return self._facility

    @facility.setter
    def facility(self: ScanConfigGenerator, facility: TelescopeFacilityEnum | str) -> None:
        """Set the facility."""
        if isinstance(facility, str):
            self._facility = TelescopeFacilityEnum[facility]
        else:
            self._facility = facility

        if self._facility == TelescopeFacilityEnum.Low:
            self._telescope = "SKALow"
        else:
            self._telescope = "SKAMid"

    @property
    def telescope(self: ScanConfigGenerator) -> str:
        """Get the current telescope.

        There is no setter for this as it depends on the facility
        """
        return self._telescope

    @property
    def observation_mode(self: ScanConfigGenerator) -> str:
        """Get current configured observation mode.

        Default value is 'VOLTAGE_RECORDER' this may change in the future
        when developing beyond AA0.5
        """
        return self._observation_mode or "VOLTAGE_RECORDER"

    @observation_mode.setter
    def observation_mode(self: ScanConfigGenerator, observation_mode: str) -> None:
        """Set the observation mode for the current test."""
        self._observation_mode = observation_mode

    @property
    def frequency_band(self: ScanConfigGenerator) -> str:
        """Get current frequency band."""
        return self._frequency_band

    @frequency_band.setter
    def frequency_band(self: ScanConfigGenerator, frequency_band: str) -> None:
        """Set the frequency band."""
        self._frequency_band = frequency_band

    def __getattr__(self: ScanConfigGenerator, key: str) -> Any:
        """Get a config value using Python attributes."""
        if key in self._config_override:
            return self._config_override[key]

        if key in self._current_config:
            return self._current_config[key]

        return self.calculate_resources()[key]

    def override_config(self: ScanConfigGenerator, key: str, value: Any) -> None:
        """Override a specific config value."""
        self._config_override[key] = value
        if key == "max_scan_length":
            self._max_scan_length = value

    def _generate_config_id(self: ScanConfigGenerator) -> str:
        """Generate a unique configuration id."""
        import random
        import string

        # create a random valid string
        characters = string.ascii_letters + string.digits + "-"
        config_id = "".join(random.choice(characters) for _ in range(20))
        while config_id in self._previous_config_ids:
            config_id = "".join(random.choice(characters) for _ in range(20))

        self._previous_config_ids.append(config_id)
        return config_id

    def _generate_csp_common_config(self: ScanConfigGenerator) -> Dict[str, Any]:
        """Generate a CSP common configuration.

        This will also generate a unique configuration id.
        """
        config_id = self._generate_config_id()
        return {
            "config_id": config_id,
            "subarray_id": 1,
            "frequency_band": self.frequency_band,
        }

    def _generate_pst_scan_config(
        self: ScanConfigGenerator, overrides: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Generate the PST Scan config with overriden values.

        If no overrides are given then this will generate a valid
        configuration.  Overrides can be used to change the configuration
        or provide an invalid configuration that can be tested.
        """
        if self._facility == TelescopeFacilityEnum.Low:
            frequency_band = "low"
        else:
            frequency_band = self.frequency_band

        frequency_band_config = get_frequency_band_config(frequency_band=frequency_band)

        pst_beam_id = str(random.randint(1, 16))

        base_request = {
            "activation_time": "2022-01-19T23:07:45Z",
            "timing_beam_id": pst_beam_id,
            "bits_per_sample": 32,
            "num_of_polarizations": 2,
            "udp_nsamp": frequency_band_config["packet_nsamp"],
            "wt_nsamp": frequency_band_config["packet_nsamp"],
            "udp_nchan": frequency_band_config["packet_nchan"],
            "num_frequency_channels": 432,
            "centre_frequency": 1000000000.0,
            # TSAMP = 207.36, using NCHAN = 432, BYTES_PER_SEC = 16666666.666666666666667
            "total_bandwidth": 1562500.0,
            "observation_mode": self.observation_mode,
            "observer_id": "jdoe",
            "project_id": "project1",
            "pointing_id": "pointing1",
            "source": "J1921+2153",
            "itrf": [5109360.133, 2006852.586, -3238948.127],
            "receiver_id": "receiver3",
            "feed_polarization": "CIRC",  # fd_poln
            "feed_handedness": 1,  # fn_hand
            "feed_angle": 10.0,  # fn_sang
            "feed_tracking_mode": "FA",  # fd_mode
            "feed_position_angle": 0.0,  # fa_req
            "oversampling_ratio": [4, 3],
            "coordinates": {"ra": "19:21:44.815", "dec": "21.884"},
            "max_scan_length": self._max_scan_length,
            "subint_duration": 30.0,
            "receptors": ["receptor1"],
            "receptor_weights": [1.0],
            "num_rfi_frequency_masks": 0,
            "rfi_frequency_masks": [],
            "destination_address": ["192.168.178.26", 9021],
            "test_vector_id": "test_vector_id",
            "num_channelization_stages": 1,
            "channelization_stages": [
                {
                    "num_filter_taps": 1,
                    "filter_coefficients": [1.0],
                    "num_frequency_channels": 10,
                    "oversampling_ratio": [4, 3],
                }
            ],
        }

        return {**base_request, **overrides, **self._config_override}

    def generate(self: ScanConfigGenerator, overrides: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Generate a configuration.

        This is the public method that should be used by test fixtures to generate
        the configuration. That overrides parameter can be used to generate an
        invalid configuration.
        """
        csp_common_request = self._generate_csp_common_config()
        configure_scan_request = self._generate_pst_scan_config(overrides)

        config = {
            "interface": "https://schema.skao.int/ska-csp-configure/2.3",
            "common": csp_common_request,
            "pst": {
                "scan": configure_scan_request,
            },
        }
        self._current_config = config

        return config

    def _get_local_host_ip(self: ScanConfigGenerator) -> str:
        """Get IP address of eth0.

        Based off https://gist.github.com/EONRaider/3b7a8ca433538dc52b09099c0ea92745.
        This is needed because the testutils container may be on a different host to
        the RECV.
        """
        import fcntl
        import socket
        import struct

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packed_iface = struct.pack("256s", "eth0".encode("utf_8"))
        packed_addr = fcntl.ioctl(sock.fileno(), 0x8915, packed_iface)[20:24]
        return socket.inet_ntoa(packed_addr)

    def calculate_resources(self: ScanConfigGenerator, overrides: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Calculate the resources for PST for current configuration.

        This is used to send requests to the UDP generator and it needs
        to know from the configuration the bandwidth, nbits, etc to
        provide a valid configuration file to be used by the UDP generator.
        """
        scan_request_params = {
            **self._current_config["common"],
            **self._current_config["pst"]["scan"],
        }

        if self._facility == TelescopeFacilityEnum.Low:
            band = "Low"
        else:
            band = "High"

        frequency_band_config = get_frequency_band_config(**scan_request_params)

        smrb_resources = calculate_smrb_subband_resources(
            beam_id=self._beam_id, request_params=scan_request_params
        )

        recv_resources = calculate_receive_subband_resources(
            beam_id=self._beam_id,
            request_params=scan_request_params,
            # these params will be added later
            data_host="127.0.0.1",
            subband_udp_ports=[10000],
        )

        recv_scan = generate_recv_scan_request(request_params=scan_request_params)

        # for now only dealing with 1 subband
        return {
            **frequency_band_config,
            **scan_request_params,
            **smrb_resources[1],
            **recv_scan,
            **recv_resources["common"],
            **recv_resources["subbands"][1],
            "beam_id": scan_request_params.get("timing_beam_id", self._beam_id),
            "band": band,
            "resolution": calculate_resolution(**recv_resources["common"]),
            "telescope": self._telescope,
            "local_host": self._get_local_host_ip(),
            **overrides,
        }
