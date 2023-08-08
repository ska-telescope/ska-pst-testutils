# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module used to generate scan configurations."""

from __future__ import annotations

__all__ = ["create_default_scan_config_generator", "create_fixed_scan_config_generator"]

import json
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Set

from ska_telmodel.csp import get_csp_config_example
from ska_telmodel.csp.version import CSP_CONFIG_VER2_4

from ska_pst_testutils.common import (
    PstObservationMode,
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


def create_default_scan_config_generator(
    beam_id: int = 1,
    frequency_band: str = "low",
    max_scan_length: float = 10.0,
) -> ScanConfigGenerator:
    """
    Create instance of a ScanConfigGenerator using default values.

    Use this method if wanting to test using a default configuration.
    The implementation of this uses the CSP v2.4 JSON
    `<https://developer.skao.int/projects/ska-telmodel/en/latest/schemas/ska-csp-configure.html>_`
    for the default values.

    :param beam_id: the ID of the beam being used to generate config for.
    :param frequency_band: the frequency band that the configuration is for.
    :param max_scan_length: the maximum scan length, default is 10 seconds.
    """
    if frequency_band == "low":
        telescope = "SKALow"
    else:
        telescope = "SKAMid"
    facility = TelescopeFacilityEnum.from_telescope(telescope)
    return ScanConfigGenerator(
        beam_id=beam_id,
        telescope=telescope,
        facility=facility,
        frequency_band=frequency_band,
        max_scan_length=max_scan_length,
    )


def create_fixed_scan_config_generator(scan_config: dict) -> ScanConfigGenerator:
    """Create instance of ScanConfigGenerator that replays provided scan configuration."""
    beam_id = int(scan_config["pst"]["scan"]["timing_beam_id"])
    frequency_band = scan_config["common"]["frequency_band"]
    if frequency_band == "low":
        facility = TelescopeFacilityEnum.Low
        telescope = "SKALow"
    else:
        facility = TelescopeFacilityEnum.Mid
        telescope = "SKAMid"
    telescope = facility.telescope
    max_scan_length = scan_config["pst"]["scan"]["max_scan_length"]

    scan_config_generator = ScanConfigGenerator(
        beam_id=beam_id,
        telescope=telescope,
        facility=facility,
        frequency_band=frequency_band,
        max_scan_length=max_scan_length,
    )
    scan_config_generator.replay_config = scan_config

    return scan_config_generator


class ScanConfigGenerator:
    """Utility class to generate Scan configuraiton."""

    def __init__(
        self: ScanConfigGenerator,
        beam_id: int,
        telescope: str,
        facility: TelescopeFacilityEnum,
        frequency_band: str,
        max_scan_length: float = 10.0,
        csp_config_version: str = CSP_CONFIG_VER2_4,
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
        self._observation_mode: PstObservationMode | None = None
        self._config_override: Dict[str, Any] = {}
        self._replay_config: dict | None = None
        self._csp_config_version = csp_config_version
        self._previous_scan_ids: Set[int] = set()

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
    def observation_mode(self: ScanConfigGenerator) -> PstObservationMode:
        """Get current configured observation mode.

        Default value is 'VOLTAGE_RECORDER' this may change in the future
        when developing beyond AA0.5
        """
        return self._observation_mode or PstObservationMode.VOLTAGE_RECORDER

    @observation_mode.setter
    def observation_mode(self: ScanConfigGenerator, observation_mode: PstObservationMode) -> None:
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

    def _generate_eb_id(self: ScanConfigGenerator) -> str:
        r"""Generate a unique execution block id.

        The EB_ID is a string that needs matches against the following
        regex: ^eb\-[a-z0-9]+\-[0-9]{8}\-[a-z0-9]+$.

        An example of this is: eb-m001-20230712-56789

        This generator will select a random char, a random number between
        0 and 999 inclusive, todays date, and a random number from 0 to
        99999 inclusive.
        """
        rand_char = random.choice(string.ascii_lowercase)
        rand1 = random.randint(0, 999)
        rand2 = random.randint(0, 99999)
        today_str = datetime.today().strftime("%Y%m%d")

        return f"eb-{rand_char}{rand1:03d}-{today_str}-{rand2:05d}"

    def _generate_csp_common_config(self: ScanConfigGenerator, eb_id: str | None = None) -> Dict[str, Any]:
        """Generate a CSP common configuration.

        This will also generate a unique configuration id.
        """
        config_id = self._generate_config_id()
        if eb_id is None:
            eb_id = self._generate_eb_id()

        return {
            "config_id": config_id,
            "subarray_id": 1,
            "frequency_band": self.frequency_band,
            "eb_id": eb_id,
        }

    def _get_pst_scan_config_example(self: ScanConfigGenerator) -> dict:
        """Get CSP configure scan example.

        This is used as a base configuration that the generator
        will override.
        """
        csp_example = get_csp_config_example(
            version=self._csp_config_version, scan=self.observation_mode.csp_scan_example_str()
        )
        return csp_example["pst"]["scan"]

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

        base_request = self._get_pst_scan_config_example()

        base_request = {
            **base_request,
            "timing_beam_id": pst_beam_id,
            "udp_nsamp": frequency_band_config["packet_nsamp"],
            "wt_nsamp": frequency_band_config["packet_nsamp"],
            "udp_nchan": frequency_band_config["packet_nchan"],
            "num_frequency_channels": 432,
            "centre_frequency": 1000000000.0,
            # TSAMP = 207.36, using NCHAN = 432, BYTES_PER_SEC = 16666666.666666666666667
            "total_bandwidth": 1562500.0,
            "observation_mode": self.observation_mode.value,
            "oversampling_ratio": frequency_band_config["oversampling_ratio"],
            "max_scan_length": self._max_scan_length,
            "subint_duration": 30.0,
            # the example has multiple receptors, only using 1 for now.
            "receptors": ["receptor1"],
            "receptor_weights": [1.0],
            "num_channelization_stages": 1,
            "channelization_stages": [
                {
                    "num_filter_taps": 1,
                    "filter_coefficients": [1.0],
                    "num_frequency_channels": 10,
                    "oversampling_ratio": frequency_band_config["oversampling_ratio"],
                }
            ],
        }

        return {**base_request, **overrides, **self._config_override}

    def generate(
        self: ScanConfigGenerator, eb_id: str | None = None, overrides: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Generate a configuration.

        This is the public method that should be used by test fixtures to generate
        the configuration. That overrides parameter can be used to generate an
        invalid configuration.
        """
        if self._replay_config is not None:
            return self._replay_config

        csp_common_request = self._generate_csp_common_config(eb_id=eb_id)
        configure_scan_request = self._generate_pst_scan_config(overrides)

        config = {
            "interface": self._csp_config_version,
            "common": csp_common_request,
            "pst": {
                "scan": configure_scan_request,
            },
        }
        self._current_config = config

        return config

    def generate_json(self: ScanConfigGenerator) -> str:
        """Generate a configuration and return it as a json string.

        This is equivalent of doing:

        .. code-block:: python

            scan_config = scan_config_generator.generate()
            scan_config_str = json.dumps(scan_config)

        """
        config = self.generate()
        return json.dumps(config)

    @property
    def replay_config(self: ScanConfigGenerator) -> dict | None:
        return self._replay_config

    @replay_config.setter
    def replay_config(self: ScanConfigGenerator, config: dict) -> None:
        self._replay_config = config
        self._current_config = config

    def reset_replay_config(self: ScanConfigGenerator) -> None:
        self._replay_config = None
        self._current_config = {}

    @property
    def curr_config_id(self: ScanConfigGenerator) -> str:
        return self._current_config["common"]["config_id"]

    @property
    def curr_config(self: ScanConfigGenerator) -> dict:
        """Get the current scan configuration."""
        return self._current_config

    @property
    def curr_config_json(self: ScanConfigGenerator) -> str:
        """Get the current scan configuration as JSON string."""
        return json.dumps(self.curr_config)

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
