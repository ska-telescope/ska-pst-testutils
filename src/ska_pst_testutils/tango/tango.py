# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module to Tango specific test utilities."""

from __future__ import annotations

__all__ = [
    "TangoDeviceCommandChecker",
    "TangoChangeEventHelper",
    "LongRunningCommandTracker",
    "TangoCommandResult",
]

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

import tango
from readerwriterlock import rwlock
from ska_tango_base.commands import ResultCode
from ska_tango_base.control_model import ObsState
from ska_tango_base.executor import TaskStatus
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

TangoCommandResult = Tuple[List[ResultCode], List[str]]


class TangoDeviceCommandChecker:
    """A convinence class used to help check a Tango Device command.

    This class can be used to check that a command executed on a
    DeviceProxy fires the correct change events for task status,
    the completion state, and any changes through the ObsState.
    """

    def __init__(
        self: TangoDeviceCommandChecker,
        tango_change_event_helper: TangoChangeEventHelper,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialise command checker."""
        self._device = device = tango_change_event_helper.device_under_test
        self._logger = logger or logging.getLogger(__name__)
        self._lrc_tracker = LongRunningCommandTracker(
            device=device,
            logger=logger,
        )

        def _subscribe(property: str) -> None:
            value = getattr(device, property)
            tango_change_event_helper.subscribe(property)
            try:
                # ignore the first event. This should be able to clear out the events
                change_event_callbacks[property].assert_change_event(value)
            except Exception:
                self._logger.warning(
                    f"Asserting {device}.{property} to be {value} failed.",
                    exc_info=True,
                )

        _subscribe("longRunningCommandProgress")
        _subscribe("longRunningCommandResult")
        _subscribe("longRunningCommandStatus")
        _subscribe("obsState")
        _subscribe("healthState")

        self.change_event_callbacks = change_event_callbacks
        self._tango_change_event_helper = tango_change_event_helper
        self._command_states: Dict[str, str] = {}
        self.prev_command_result: ResultCode | None = None
        self.prev_command_result_message: str | None = None

    def assert_command(  # noqa: C901 - override checking of complexity for this test
        self: TangoDeviceCommandChecker,
        command: Callable[[], TangoCommandResult],
        expected_result_code: ResultCode = ResultCode.QUEUED,
        expected_command_result: Optional[str] = '"Completed"',
        expected_command_status_events: List[TaskStatus] = [
            TaskStatus.QUEUED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
        ],
        expected_obs_state_events: List[ObsState] = [],
        timeout: float = 5.0,
    ) -> None:
        """Assert that the command has the correct result and events.

        This method has sensible defaults of the expected result code,
        the overall result, and the status events that the command
        goes through, and by default asserts that the ObsState model
        doesn't change.

        :param command: a callable on the device proxy.
        :param expected_result_code: the expected result code returned
            from the call. The default is ResultCode.QUEUED.
        :param expected_command_result: the expected command result
            when the command completes. The default is "Completed".
        :param expected_command_status_events: a list of expected
            status events of the command, these should be in the
            order the events happen. Default expected events are:
            [TaskStatus.QUEUED, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        :param expected_obs_state_events: the expected events of the ObsState
            model. The default is an empty list, meaning no events expected.
        :param timeout: expected length of time for the results of the command
            to take.
        """
        current_obs_state = self._device.obsState

        [[self.prev_command_result], [self.prev_command_result_message]] = command()
        assert self.prev_command_result == expected_result_code

        command_id = self.prev_command_result_message

        if len(expected_command_status_events) > 0:
            self._lrc_tracker.wait_for_command_to_complete(command_id=command_id, timeout=timeout)
            self._lrc_tracker.assert_command_status_events(
                command_id=command_id,
                expected_command_status_events=expected_command_status_events,
            )

        if expected_command_result is not None:
            self.change_event_callbacks["longRunningCommandResult"].assert_change_event(
                (self.prev_command_result_message, expected_command_result),
            )

        if expected_obs_state_events and [current_obs_state] != expected_obs_state_events:
            for expected_obs_state in expected_obs_state_events:
                self._logger.debug(f"Checking next obsState event is {expected_obs_state.name}")
                self.change_event_callbacks["obsState"].assert_change_event(expected_obs_state.value)
        else:
            self._logger.debug("Checking obsState does not change.")
            self.change_event_callbacks["obsState"].assert_not_called()


class TangoChangeEventHelper:
    """Internal testing class used for handling change events."""

    def __init__(
        self: TangoChangeEventHelper,
        device_under_test: tango.DeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialise change event helper."""
        self.device_under_test = device_under_test
        self.change_event_callbacks = change_event_callbacks
        self.subscriptions: Dict[str, int] = {}
        self.logger = logger or logging.getLogger(__name__)

    def __del__(self: TangoChangeEventHelper) -> None:
        """Free resources held."""
        self.release()

    def subscribe(self: TangoChangeEventHelper, attribute_name: str) -> None:
        """Subscribe to change events of an attribute.

        This returns a MockChangeEventCallback that can
        then be used to verify changes.
        """

        def _handle_evt(*args: Any, **kwargs: Any) -> None:
            self.logger.debug(f"Event recevied with: args={args}, kwargs={kwargs}")
            self.change_event_callbacks[attribute_name](*args, **kwargs)

        subscription_id = self.device_under_test.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            _handle_evt,
        )
        self.logger.debug(f"Subscribed to events of '{attribute_name}'. subscription_id = {subscription_id}")
        self.subscriptions[attribute_name] = subscription_id

    def release(self: TangoChangeEventHelper) -> None:
        """Release any subscriptions that are held."""
        for name, subscription_id in self.subscriptions.items():
            self.logger.debug(f"Unsubscribing to '{name}' with subscription_id = {subscription_id}")
            self.device_under_test.unsubscribe_event(subscription_id)
        self.subscriptions.clear()


class LongRunningCommandTracker:
    """A convinence class used to help check a Tango Device command.

    This class can be used to check that a command executed on a
    :py:class:`DeviceProxy` fires the correct change events
    for task status, the completion state, and any changes through
    the :py:class:`ObsState`.
    """

    def __init__(
        self: LongRunningCommandTracker, device: tango.DeviceProxy, logger: logging.Logger | None = None
    ) -> None:
        """Initialise command checker."""
        self._device = device
        self._lock = rwlock.RWLockWrite()
        self._command_status_events: Dict[str, List[TaskStatus]] = {}
        self._logger = logger or logging.getLogger(__name__)
        self._condvar = threading.Condition()
        self.subscription_id = self._device.subscribe_event(
            "longRunningCommandStatus",
            tango.EventType.CHANGE_EVENT,
            self._handle_evt,
        )

    def _handle_evt(self: LongRunningCommandTracker, event: tango.EventData) -> None:
        try:
            self._logger.debug(f"Received event for longRunningCommandStatus, event = {event}")
            if event.err:
                self._logger.warning(f"Received failed change event: error stack is {event.errors}.")
                return
            elif event.attr_value is None:
                warning_message = (
                    "Received change event with empty value. Falling back to manual "
                    f"attribute read. Event.err is {event.err}. Event.errors is\n"
                    f"{event.errors}."
                )
                self._logger.warning(warning_message)
                value = self._device.longRunningCommandStatus
            else:
                value = event.attr_value

            if isinstance(value, tango.DeviceAttribute):
                value = value.value

            if value is None:
                return

            self._logger.debug(
                f"Received event callback for {self._device}.longRunningCommandStatus with value: {value}"
            )

            # LRC command value is a tuple in the form of (command1_id, status_1, command2_id, status_2, ...)
            # this converts a tuple to a dictionary
            value = list(value)
            values: Dict[str, TaskStatus] = {
                value[i]: TaskStatus[value[i + 1]] for i in range(0, len(value), 2)
            }

            with self._lock.gen_wlock():
                for command_id, status in values.items():
                    if command_id not in self._command_status_events:
                        self._command_status_events[command_id] = list()

                    curr_command_status_events = self._command_status_events[command_id]
                    # add status to previous states if
                    if len(curr_command_status_events) == 0 or curr_command_status_events[-1] != status:
                        curr_command_status_events.append(status)

                with self._condvar:
                    self._condvar.notify_all()
        except Exception:
            self._logger.exception("Error in handling of event", exc_info=True)

    def assert_command_status_events(
        self: LongRunningCommandTracker,
        command_id: str,
        expected_command_status_events: List[TaskStatus] = [
            TaskStatus.QUEUED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
        ],
    ) -> None:
        """Assert that the command has the correct status events.

        :param command_id: the id of the command to assert events against.
        :param expected_command_status_events: a list of expected
            status events of the command, these should be in the
            order the events happen. Default expected events are:
            [TaskStatus.QUEUED, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        """
        with self._lock.gen_rlock():
            assert (
                command_id in self._command_status_events
            ), f"Expected command status events for command {command_id}"
            assert expected_command_status_events == self._command_status_events[command_id], (
                f"Expected command status events to be {expected_command_status_events} "
                f"but received {self._command_status_events[command_id]}"
            )

    def wait_for_command_to_complete(
        self: LongRunningCommandTracker, command_id: str, timeout: float = 5.0
    ) -> None:
        """Wait for a command to complete.

        This waits for the a given command to complete within a given timeout.
        A command is considered complete if the last status event is either:
        TaskStatus.COMPLETED, TaskStatus.ABORTED, TaskStatus.FAILED, or
        TaskStatus.REJECTED.

        :param command_id: the id of the command to assert events against.
        """

        def _command_complete() -> bool:
            with self._lock.gen_rlock():
                if command_id not in self._command_status_events:
                    return False

                curr_status_events = self._command_status_events[command_id]
                if len(curr_status_events) == 0:
                    return False

                return curr_status_events[-1] in [
                    TaskStatus.COMPLETED,
                    TaskStatus.ABORTED,
                    TaskStatus.FAILED,
                    TaskStatus.REJECTED,
                ]

        with self._condvar:
            result = self._condvar.wait_for(_command_complete, timeout=timeout)
            if result:
                return

            raise TimeoutError(f"Expected command {command_id} to complete in {timeout:.1f}s")
