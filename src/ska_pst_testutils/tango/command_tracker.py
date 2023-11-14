# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module class file for tracking commands."""

from __future__ import annotations

__all__ = ["CommandTracker"]

import logging
import re
from typing import Any, Callable, Dict, Optional

from ska_control_model import ObsState
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevFailed

from ska_pst_testutils.common import PstDeviceProxy

from .tango import TangoChangeEventHelper, TangoDeviceCommandChecker


class CommandTracker:
    """Class to track the progress and results of commands on a PstDeviceProxy.

    This class also uses the `TangoDeviceCommandChecker` which is more low
    level to check for updates of the long running process values. This
    provides a high level view of a command.  It also will record if the
    commands fail and what was the state of the device proxy before the command
    was executed.
    """

    def __init__(
        self: CommandTracker,
        device_proxy: PstDeviceProxy,
        change_event_callbacks: MockTangoEventCallbackGroup,
        logger: logging.Logger | None = None,
        default_timeout: float = 5.0,
    ) -> None:
        """Create an instance of the command tracker.

        :param device_proxy: the device proxy to track commands against.
        :param change_event_callbacks: the ska-tango-testuils helper to assert change
            events against.
        :param logger: the logger to use for the instance.
        :param default_timeout: the default timeout for a command to complete. Default 5.0
        """
        # need the tango classes here
        self.logger = logger or logging.getLogger(__name__)
        self.device_proxy = device_proxy
        self.tango_change_event_helper = TangoChangeEventHelper(
            device_under_test=self.device_proxy,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

        self.tango_device_command_checker = TangoDeviceCommandChecker(
            tango_change_event_helper=self.tango_change_event_helper,
            change_event_callbacks=change_event_callbacks,
            logger=logger,
        )

        self.prev_command_err: Optional[Exception] = None
        self.prev_obs_state: ObsState = ObsState.IDLE
        self.prev_command: str = ""
        self._command_dict: Dict[str, Callable[..., None]] = {
            "ConfigureScan": self._configure_scan,
            "GoToIdle": self._goto_idle,
            "Scan": self._scan,
            "Abort": self._abort,
            "EndScan": self._end_scan,
            "GoToFault": self._goto_fault,
            "ObsReset": self._obsreset,
            "On": self._on,
            "Off": self._off,
        }
        self.default_timeout = default_timeout

    def teardown(self: CommandTracker) -> None:
        """Teardown the command tracker.

        This releases all of the subscriptions and change events used by the tracker.
        """
        self.tango_change_event_helper.release()

    def assert_previous_command_rejected(self: CommandTracker) -> None:
        """Assert previous command was rejected due to invalid state."""
        self.assert_previous_command_error_message_matches(
            (
                f"ska_tango_base.faults.StateModelError: {self.prev_command} command "
                f"not permitted in observation state {self.prev_obs_state.name}"
            )
        )

    def assert_previous_command_failed(self: CommandTracker) -> None:
        """Assert previous command failed."""
        assert self.prev_command_err is not None, "previous command error is not initialised"

    def assert_previous_command_error_message_matches(
        self: CommandTracker, expected_message_regexp: str
    ) -> None:
        """Assert previous command error message is equal to the argument."""
        assert self.prev_command_err is not None, "previous command error is not initialised"
        if isinstance(self.prev_command_err, DevFailed):
            got_message = self.prev_command_err.args[0].desc.strip()
        else:
            got_message = self.tango_device_command_checker.prev_command_result_message
        self.logger.info(f"Got error msg: '{got_message}'")
        self.logger.info(f"Expected error msg: '{expected_message_regexp}'")
        regexp = re.compile(expected_message_regexp)
        assert (
            regexp.search(got_message) is not None
        ), f"error message '{got_message}' doesn't match expected message '{expected_message_regexp}'"

    def perform_command(
        self: CommandTracker,
        command: str,
        raise_exception: bool = False,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Execute the command.

        This method can also optionally reraise the exception during the call
        rather than storing the exception.  This should be used during the
        setup and teardown of the system.
        """
        self.prev_obs_state = self.device_proxy.obsState
        self.prev_command_err = None

        timeout = timeout or self.default_timeout

        try:
            self._command_dict[command](timeout=timeout, **kwargs)
        except KeyError:
            self.logger.error(f"Unknown command '{command}' sent to command tracker")
            raise
        except Exception as e:
            if raise_exception:
                raise e

            self.prev_command_err = e
        finally:
            self.prev_command = command

    def _configure_scan(
        self: CommandTracker,
        scan_configuration: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Perform a ConfigureScan request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.ConfigureScan(scan_configuration),
            expected_obs_state_events=[
                ObsState.CONFIGURING,
                ObsState.READY,
            ],
            **kwargs,
        )

    def _goto_idle(
        self: CommandTracker,
        **kwargs: Any,
    ) -> None:
        """Perform a GoToIdle request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.GoToIdle(),
            expected_obs_state_events=[
                ObsState.IDLE,
            ],
            **kwargs,
        )

    def _scan(self: CommandTracker, scan_id: int, **kwargs: Any) -> None:
        """Perform a Scan request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.Scan(str(scan_id)),
            expected_obs_state_events=[
                ObsState.SCANNING,
            ],
            **kwargs,
        )

    def _end_scan(self: CommandTracker, **kwargs: Any) -> None:
        """Perform an EndScan request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.EndScan(),
            expected_obs_state_events=[
                ObsState.READY,
            ],
            **kwargs,
        )

    def _abort(
        self: CommandTracker,
        **kwargs: Any,
    ) -> None:
        """Perform an Abort request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.Abort(),
            expected_result_code=ResultCode.STARTED,
            expected_obs_state_events=[
                ObsState.ABORTING,
                ObsState.ABORTED,
            ],
            **kwargs,
        )

    def _goto_fault(self: CommandTracker, fault_message: str, **kwargs: Any) -> None:
        """Perform a GoToFault request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.GoToFault(fault_message),
            expected_obs_state_events=[
                ObsState.FAULT,
            ],
            **kwargs,
        )

    def _obsreset(
        self: CommandTracker,
        **kwargs: Any,
    ) -> None:
        """Perform an ObsReset request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.ObsReset(),
            expected_obs_state_events=[
                ObsState.RESETTING,
                ObsState.IDLE,
            ],
            **kwargs,
        )

    def _on(
        self: CommandTracker,
        **kwargs: Any,
    ) -> None:
        """Perform an On request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.On(),
            expected_obs_state_events=[ObsState.IDLE],
            **kwargs,
        )

    def _off(
        self: CommandTracker,
        **kwargs: Any,
    ) -> None:
        """Perform an Off request on device proxy."""
        self.tango_device_command_checker.assert_command(
            lambda: self.device_proxy.Off(),
            **kwargs,
        )
