# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains the pytest tests for the Device Proxy and Factory class."""

import logging
from unittest.mock import ANY, MagicMock

import tango
from ska_tango_base.control_model import AdminMode
from tango import GreenMode

from ska_pst_testutils.common import DeviceProxyFactory


def test_factory_returns_device_proxy() -> None:
    """Test that DeviceProxyFactory returns same proxy."""
    DeviceProxyFactory._proxy_supplier = MagicMock()

    first = DeviceProxyFactory.get_device("foo/bar/car")

    assert first is not None

    second = DeviceProxyFactory.get_device("foo/bar/car")
    assert first == second

    third = DeviceProxyFactory.get_device("x/y/z")
    assert first != third


def test_factory_calls_supplier() -> None:
    """Test that the factory uses the supplier and given parameters."""
    supplier = MagicMock()
    DeviceProxyFactory._proxy_supplier = supplier
    logger = logging.getLogger(__name__)

    device = DeviceProxyFactory.get_device(
        fqdn="a/b/c",
        green_mode=GreenMode.Asyncio,
        logger=logger,
    )

    supplier.assert_called_once_with("a/b/c", green_mode=GreenMode.Asyncio)
    assert device.fqdn == "a/b/c"
    assert device._logger == logger


def test_pst_device_proxy_subscribe_to_event() -> None:
    """Test that the factory sets up an event subscription."""
    supplier = MagicMock()
    DeviceProxyFactory._proxy_supplier = supplier

    device = DeviceProxyFactory.get_device(fqdn="test/recv/0")
    device._device.subscribe_event.return_value = 1138

    callback = MagicMock()
    subscription = device.subscribe_change_event("obsState", callback=callback, stateless=False)

    assert subscription is not None
    assert subscription.subscribed
    assert "obsState" in device._subscriptions
    assert callback in subscription._callbacks

    callback2 = MagicMock()
    subscription2 = device.subscribe_change_event("obsState", callback=callback2, stateless=False)
    assert subscription == subscription2
    assert subscription2._callbacks == [callback, callback2]
    assert "obsState" in device._subscriptions

    device._device.subscribe_event.assert_called_once_with(
        "obsState",
        tango.EventType.CHANGE_EVENT,
        ANY,
        stateless=False,
    )

    subscription.unsubscribe()
    assert not subscription.subscribed
    assert subscription.callbacks == []
    assert "obsState" not in device._subscriptions
    device._device.unsubscribe_event.assert_called_once_with(subscription._subscription_id)


def test_pst_device_proxy_sends_requests_to_device() -> None:
    """Test that the device proxy is a transparent wrapper of device."""
    supplier = MagicMock()
    DeviceProxyFactory._proxy_supplier = supplier

    proxy = DeviceProxyFactory.get_device(fqdn="test/recv/0")

    device = proxy._device

    proxy.Scan()
    device.Scan.assert_called()

    device.data_receive_rate = 3
    assert proxy.data_receive_rate == 3

    proxy.adminMode = AdminMode.ONLINE
    assert device.adminMode == AdminMode.ONLINE
