# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module class to read decode and inspect the channel block configuration."""

from __future__ import annotations

__all__ = ["ChannelBlockValidator"]

import json
import logging
import re
from typing import Any, Dict, List


class _ChannelBlock:
    """A class to store and validate configuration of a single channel block."""

    def __init__(self: _ChannelBlock, index: int, config: Dict[str, Any]) -> None:

        # ( [0-9]|[1-9][0-9] | 1[0-9]{2} | 2[0-4][0-9] | 25[0-5])

        self.validated = False
        self.ipv4_regex = re.compile(
            r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}"
            "([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        )
        self.port_range = [10000, 32768]
        self.channel_range = [0, 82943]

        self.index = index
        required_keys = [
            "destination_host",
            "destination_port",
            "start_pst_channel",
            "num_pst_channels",
        ]
        for key in required_keys:
            assert key in config, f"channel_block {self.index} missing required key {key}"

        self.host = config["destination_host"]
        self.port = config["destination_port"]
        self.start_channel = config["start_pst_channel"]
        self.num_channels = config["num_pst_channels"]

        assert type(self.port) == int, "channel_block {self.index} destination_port was not an integer"
        assert (
            type(self.start_channel) == int
        ), "channel_block {self.index} start_pst_channel was not an integer"
        assert (
            type(self.start_channel) == int
        ), "channel_block {self.index} num_pst_channels was not an integer"

        self.lowest_channel = self.start_channel
        self.highest_channel = (self.start_channel + self.num_channels) - 1

    def validate_config(self: _ChannelBlock) -> None:
        """Validate the channel block configuration parameters."""
        assert (
            self.ipv4_regex.match(self.host) is not None
        ), f"channel block {self.index} destination_host [{self.host}] invalid IPv4 address"

        assert self.port_range[0] <= self.port <= self.port_range[1], (
            f"channel block {self.index} destination_port not in range "
            f"{self.port_range[0]}-{self.port_range[1]}"
        )

        assert self.lowest_channel >= self.channel_range[0], (
            f"channel block {self.index} lowest channel [{self.lowest_channel} "
            f"below minimum [{self.channel_range[0]}]"
        )

        assert self.highest_channel <= self.channel_range[1], (
            f"channel block {self.index} highest channel [{self.highest_channel} "
            f"above maximum [{self.channel_range[1]}]"
        )

        assert self.lowest_channel < self.highest_channel, (
            f"channel block {self.index} lowest channel [{self.lowest_channel} "
            f"not less than highest channel [{self.highest_channel}]"
        )

        self.validated = True

    def validate_overlapping(self: _ChannelBlock, all_channel_blocks: List[_ChannelBlock]) -> None:
        """Check that this channel block does not overlap with others."""
        for channel_block in all_channel_blocks:
            if channel_block.index != self.index:
                assert (
                    channel_block.highest_channel < self.lowest_channel
                    or channel_block.lowest_channel > self.highest_channel
                ), (
                    f"channel block {channel_block.index} channels overlap with channel "
                    f"block {self.index}"
                )

                assert not (channel_block.host == self.host and channel_block.port == self.port), (
                    f"channel block {channel_block.index} endpoint [{channel_block.host}:"
                    f"{channel_block.port}] same as channel block {self.index} [{self.host}:{self.port}]"
                )


class ChannelBlockValidator:
    """Class that can be used to read and validate channel block configuration."""

    def __init__(
        self: ChannelBlockValidator, encoded_json: str, logger: logging.Logger | None = None
    ) -> None:
        """Create instance of channel block validator."""
        self.logger = logger or logging.getLogger(__name__)
        self.cb_range = [1, 8]
        self.required_keys = ["num_channel_blocks", "channel_blocks"]
        self.config = self.unpack(encoded_json)

    def unpack(self: ChannelBlockValidator, encoded_json: str) -> Dict[Any, Any]:
        """Unpack the json into a dict."""
        try:
            self.logger.info(f"channel block config {encoded_json}")
            return json.loads(encoded_json)
        except json.JSONDecodeError as e:
            self.logger.exception(f"channel block configuration was invalid JSON: {encoded_json}")
            raise AssertionError("channel block configuration was invalid JSON") from e

    def is_empty(self: ChannelBlockValidator) -> bool:
        """Check the the channel block configuration is empty."""
        return self.config == {}

    def validate(
        self: ChannelBlockValidator,
    ) -> None:  # noqa: C901 - override complexity
        """Test if channel block configuration is valid."""
        # check for top level keys
        for key in self.required_keys:
            assert key in self.config, f"channel block configuration missing required key '{key}'"

        # ensure the number of channel blocks is valid
        assert (
            self.cb_range[0] <= self.config["num_channel_blocks"] <= self.cb_range[1]
        ), f"num_channel_blocks not in range {self.cb_range}"

        assert len(self.config["channel_blocks"]) == self.config["num_channel_blocks"], (
            f"mismatch between num_channel_blocks {self.config['num_channel_blocks']} and "
            f"the number of channel blocks[{len(self.config['channel_blocks'])}]"
        )

        channel_blocks = []
        self.logger.debug(f"channel_blocks={self.config['channel_blocks']}")
        for i in range(self.config["num_channel_blocks"]):
            channel_blocks.append(_ChannelBlock(i, self.config["channel_blocks"][i]))

        # validate the individual configuration in each channel block
        for channel_block in channel_blocks:
            channel_block.validate_config()

        # check the channel ranges do not overlap between channel blocks
        for channel_block in channel_blocks:
            channel_block.validate_overlapping(channel_blocks)
