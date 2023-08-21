# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module class file for providing a testing wrapper class around device proxies."""

from __future__ import annotations

import logging
import time
from functools import partial
from typing import Any, Callable, Generator, List, Tuple, TypeAlias

import tango
from readerwriterlock import rwlock
from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode
from ska_tango_base.executor import TaskStatus

from .tango import LongRunningCommandTracker, _TangoAttributeEventSubscription

TangoCommandResult: TypeAlias = Tuple[List[ResultCode], List[str]]


class _MonitorAttributesFilter(logging.Filter):
    def filter(self: _MonitorAttributesFilter, record: logging.LogRecord) -> bool:
        if hasattr(record, "monitor_attr"):
            for k, v in record.monitor_attr.items():
                record.msg = record.msg + f"\n{k}: {v}"

        return super().filter(record)


MONITOR_ATTRIBUTES_FILTER: _MonitorAttributesFilter = _MonitorAttributesFilter()


class PstTestDeviceProxy:
    """A class for use when testing a PST Tango Device.

    This class is designed as a lightweight proxy that wraps a
    :py:class:`tango.DeviceProxy`. This allows for automated testing
    or using in a notebook to block on the command calls rather than
    assuming the calls have finished.

    All the commands exposed on this class do not check the current
    state of the remote device. The remote device is in control of
    checking state and rejecting methods that are or are not allowed.
    """

    def __init__(
        self: PstTestDeviceProxy,
        fqdn: str,
        logger: logging.Logger | None = None,
        command_timeout: float = 30.0,
    ) -> None:
        """Create instance of device proxy.

        :param fqdn: the fully qualified domain name (FQDN) of the Tango device.
        :param logger: the optional logger to used when instances of this class
            needs to log output.
        """
        logger = logger or logging.getLogger(__name__)
        logger.addFilter(MONITOR_ATTRIBUTES_FILTER)
        super().__setattr__("logger", logger)

        device_proxy = tango.DeviceProxy(fqdn)
        command_tracker = LongRunningCommandTracker(device=device_proxy, logger=logger)
        super().__setattr__("_device", device_proxy)
        super().__setattr__("command_tracker", command_tracker)
        super().__setattr__("fqdn", fqdn)
        super().__setattr__("_curr_attr_values", {})
        super().__setattr__("_rw_lock", rwlock.RWLockWrite())
        super().__setattr__("command_timeout", command_timeout)

        # attribute subscriptions
        subscriptions = {
            _TangoAttributeEventSubscription(
                device=device_proxy,
                attribute=attribute,
                evt_handler=partial(self._store_event, attribute),
                logger=logger,
            )
            for attribute in [
                "dataReceiveRate",
                "dataReceived",
                "dataDropRate",
                "dataDropped",
                "dataRecordRate",
                "dataRecorded",
                "availableDiskSpace",
                "availableRecordingTime",
                "ringBufferUtilisation",
            ]
        }
        super().__setattr__("_subscriptions", subscriptions)

    def _store_event(self: PstTestDeviceProxy, attribute: str, value: Any) -> None:
        with self._rw_lock.gen_wlock():
            self._curr_attr_values[attribute] = value

    def _yield_attr_values(self: PstTestDeviceProxy, attr: str) -> Generator[Any, None, None]:
        while True:
            yield self._device.read_attribute(attr).value
            time.sleep(1)

    def _wait_for_attribute_value(self: PstTestDeviceProxy, attr: str, desired_value: Any) -> None:
        for value in self._yield_attr_values(attr):
            if value == desired_value:
                return

    def _wait_for_command(self: PstTestDeviceProxy, command: Callable[..., TangoCommandResult]) -> None:
        [[result], [msg_or_command_id]] = command()
        result = ResultCode(result)
        if result not in [ResultCode.STARTED, ResultCode.QUEUED]:
            self.logger.warning(f"Result code of command = {result}. Message = {msg_or_command_id}")
        else:
            self.logger.info(f"Long running command result = {result.name}, command id = {msg_or_command_id}")
            task_status = self.command_tracker.wait_for_command_to_complete(
                command_id=msg_or_command_id, timeout=self.command_timeout
            )
            if task_status == TaskStatus.FAILED:
                result = self._device.longRunningCommandResult
                self.logger.warning(f"Command failed. The result message = {result}")

    def On(self: PstTestDeviceProxy) -> None:
        """Call On command on remote device."""
        self._wait_for_command(command=lambda: self._device.On())

    def Off(self: PstTestDeviceProxy) -> None:
        """Call Off command on remote device."""
        self._wait_for_command(command=lambda: self._device.Off())

    def ConfigureScan(self: PstTestDeviceProxy, scan_configuration: str) -> None:
        """Call ConfigureScan on remote device.

        This method takes a scan configuration that is passed to the device proxy.

        :param scan_configuration: a JSON string of the scan configuration to be
            sent to the remote device.
        """
        self._wait_for_command(command=lambda: self._device.ConfigureScan(scan_configuration))

    def Scan(self: PstTestDeviceProxy, scan_id: str) -> None:
        """Call Scan on remote device.

        This will put the remote device in to a SCANNING state.
        """
        self._wait_for_command(command=lambda: self._device.Scan(scan_id))

    def EndScan(self: PstTestDeviceProxy) -> None:
        """Call EndScan on remote device."""
        self._wait_for_command(command=lambda: self._device.EndScan())

    def GoToIdle(self: PstTestDeviceProxy) -> None:
        """Call GoToIdle on remote device."""
        self._wait_for_command(command=lambda: self._device.GoToIdle())

    def GoToFault(self: PstTestDeviceProxy, fault_msg: str) -> None:
        """Call GoToFault on remote device."""
        self._wait_for_command(command=lambda: self._device.GoToFault(fault_msg))

    def Abort(self: PstTestDeviceProxy) -> None:
        """Call Abort on remote device."""
        self._wait_for_command(command=lambda: self._device.Abort())

    def ObsReset(self: PstTestDeviceProxy) -> None:
        """Call ObsReset on remote device."""
        self._wait_for_command(command=lambda: self._device.ObsReset())

    def state(self: PstTestDeviceProxy) -> tango.AdminMode:
        """Get the current admin mode state of the remote device."""
        return self._device.state()

    def __setattr__(self: PstTestDeviceProxy, name: str, value: Any) -> None:
        """Set an attribute value on the remote device."""
        self._device.write_attribute(name, value)
        self._wait_for_attribute_value(attr=name, desired_value=value)

    def __getattr__(self: PstTestDeviceProxy, name: str) -> Any:
        """Get an attribute value from the remote device."""
        return self._device.read_attribute(name).value

    def get_property(self: PstTestDeviceProxy, propname: str) -> Any:
        """Get the value of a device property.

        This just proxies through to the `tango.DeviceProxy.get_property`
        """
        return self._device.get_property(propname)

    def display_monitoring(self: PstTestDeviceProxy) -> None:
        """Display current values of some monitored attributes on remote device."""
        with self._rw_lock.gen_rlock():
            self.logger.info("Current attribute values:", extra={"monitor_attr": self._curr_attr_values})

    def monitor(self: PstTestDeviceProxy) -> None:
        """Start background monitoring of values of remote device.

        This method will start a background process to log out the current
        monitored values. This is done at a rate given by the monitoring
        polling rate on the remote device.
        """
        import multiprocessing

        monitoring_polling_rate = self.monitoringPollingRate

        def _monitor() -> None:
            self.logger.info(f"Starting to monitor {self.fqdn}")
            self.logger.info(f"Monitoring polling rate: {monitoring_polling_rate}ms")

            while self.obsState == ObsState.SCANNING:
                try:
                    self.display_monitoring()
                    time.sleep(monitoring_polling_rate / 1000.0)
                except Exception:
                    self.logger.exception("Exception occured while monitoring.", exc_info=True)
            self.logger.info(f"Monitoring is exiting as state is: {ObsState(self.obsState)}")

        multiprocessing.Process(target=_monitor).start()
