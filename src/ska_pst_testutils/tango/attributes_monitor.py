# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module class file for helping with attribute monitoring."""

from __future__ import annotations

__all__ = [
    "AttributesMonitor",
]

import functools
from typing import Any, Callable, Dict, List

import backoff
from readerwriterlock import rwlock

from ska_pst_testutils.common import ChangeEventSubscription, PstDeviceProxy


class _AttributeHistory:
    """Class representing the history of an attribute."""

    def __init__(self: _AttributeHistory, attribute_name: str, initial_value: Any) -> None:
        """Create instance of an attribute history.

        :param attribute_name: the name of the attribute to track the history of.
        :param initial_value: the initial value of the attribute.
        """
        self.attribute_name = attribute_name
        self._lock = rwlock.RWLockWrite()
        self._history = [initial_value]

    @property
    def current_value(self: _AttributeHistory) -> Any:
        with self._lock.gen_rlock():
            return self._history[-1]

    def _update_value(self: _AttributeHistory, value: Any) -> None:
        """Update the current value of the attribute."""
        with self._lock.gen_wlock():
            if self._history[-1] != value:
                self._history.append(value)

    @property
    def history(self: _AttributeHistory) -> List[Any]:
        """Get history of the attribute."""
        with self._lock.gen_rlock():
            # do a shallow copy. Don't return actual
            # list as that could update
            return [*self._history]

    def wait_for_update(self: _AttributeHistory, timeout: float = 5.0) -> None:
        """Wait for the attribute to update."""
        # get current value - this property has
        # a read lock.
        current_value = self.current_value

        def _raise_timeout_error(*args: Any, **kwargs: Any) -> None:
            raise TimeoutError()

        @backoff.on_predicate(
            backoff.expo,
            on_giveup=_raise_timeout_error,
            factor=0.1,
            max_time=timeout,
        )
        def _check_updated() -> bool:
            # don't use a lock here as not needed.
            return current_value != self._history[-1]

        _check_updated()


class AttributesMonitor:
    """Class used to monitor the attributes of a Tango device.

    This class can be used to track multiple attributes of a Tango class
    and then be used to assert values or wait for when an attribute is
    updated.

    Creating the instance of this class does nothing.  The `setup` method
    must be called afterwards to ensure that attributes are monitored.
    """

    def __init__(
        self: AttributesMonitor,
        device_proxy: PstDeviceProxy,
        attribute_names: List[str],
    ) -> None:
        """Create an instance of a attribute monitor.

        :param device_proxy: the device proxy to monitor attribute values for.
        :param attribute_names: the name of all the attributes to monitor.
        """
        self.device_proxy = device_proxy
        self.attribute_names = attribute_names
        self.attribute_histories: Dict[str, _AttributeHistory] = {}
        self.attribute_subscriptions: Dict[str, ChangeEventSubscription] = {}
        self.previous_attribute_values: Dict[str, Any] = {}

    def __del__(self: AttributesMonitor) -> None:
        """Ensure cleanup on delete."""
        self.teardown()

    def setup(self: AttributesMonitor) -> None:
        """Set up monitoring for attributes."""
        for attr in self.attribute_names:
            initial_value = getattr(self.device_proxy, attr)
            self.previous_attribute_values[attr] = initial_value
            self.attribute_histories[attr] = _AttributeHistory(
                attribute_name=attr, initial_value=initial_value
            )
            self.attribute_subscriptions[attr] = self.device_proxy.subscribe_change_event(
                attr, functools.partial(self._handle_attribute_event, attr)
            )

    def teardown(self: AttributesMonitor) -> None:
        """Teardown the monitor.

        This will unsubscribe from Tango events of the attributes.
        """
        for s in self.attribute_subscriptions.values():
            s.unsubscribe()

        self.attribute_subscriptions.clear()
        self.attribute_histories.clear()

    def _handle_attribute_event(
        self: AttributesMonitor,
        attribute: str,
        attribute_value: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Handle an event that updates the attribute on the Tango device.

        Note we will get the initial value being sent to us via Tango.
        """
        attr_history = self.attribute_histories[attribute]
        attr_history._update_value(attribute_value)

    @property
    def current_attribute_values(self: AttributesMonitor) -> Dict[str, Any]:
        """Get current attribute values for device."""
        self.capture_current_values()
        return self.previous_attribute_values

    def capture_current_values(self: AttributesMonitor) -> None:
        """Capture the current values to allow for asserting of updates later."""
        self.previous_attribute_values = {k: a.current_value for k, a in self.attribute_histories.items()}

    def assert_attribute(
        self: AttributesMonitor, attribute: str, value_assertion: Callable[..., bool]
    ) -> None:
        """Assert and attribute has a given value.

        This is a helper method to get the attribute's history and then passes it
        to the value_assertion callable.

        :param attribute: the name of the attribute to assert against.
        :param value_assertion: a callable to assert against the latest value of the attribute.
        """
        value = self.attribute_histories[attribute].current_value
        assert value_assertion(
            value
        ), f"Atrribute '{attribute}' did not meet value assertion. Current value = {value}"

    def assert_attribute_values_changed(self: AttributesMonitor) -> None:
        """Assert that attribute values have changed since last check."""
        prev_values = self.previous_attribute_values
        curr_values = self.current_attribute_values

        assert prev_values != curr_values

    def assert_attribute_values_not_changed(self: AttributesMonitor) -> None:
        """Assert that attribute values have not changed since last check."""
        prev_values = self.previous_attribute_values
        curr_values = self.current_attribute_values

        assert prev_values == curr_values

    def wait_for_attribute_update(self: AttributesMonitor, attribute_name: str, timeout: float) -> None:
        """Wait for attribute to be updated.

        Waits until there has been an update for the specific attribute or a timeout has occured.

        :param attribute_name: the attribet to wait for an update of.
        :param timeout: how long to wait for an update before raising an exception.
        """
        self.attribute_histories[attribute_name].wait_for_update(timeout=timeout)
