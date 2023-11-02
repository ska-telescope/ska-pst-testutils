# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module defines elements of the pytest test harness shared by all tests."""

import random

import pytest

from ska_pst_testutils.scan_config import ScanIdFactory


@pytest.fixture(scope="session")
def scan_id_factory() -> ScanIdFactory:
    """Create an instance of ScanIdFactory."""
    return ScanIdFactory()


@pytest.fixture
def scan_id(scan_id_factory: ScanIdFactory) -> int:
    """Generate a random scan id."""
    return scan_id_factory.generate_scan_id()


@pytest.fixture
def scanlen() -> int:
    """Generate a random scan length between 1 and 10 seconds."""
    return random.randint(1, 10)


@pytest.fixture
def channel_block_configuration() -> dict:
    """Generate a simulated channel block configuration."""
    return {
        "channel_blocks": [
            {
                "destination_host": "127.0.0.1",
                "destination_port": 30000,
            },
        ],
    }
