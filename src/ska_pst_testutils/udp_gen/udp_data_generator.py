# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module to used for sending UDP packets."""

from __future__ import annotations

import enum
import logging
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, TextIO


class _GeneratingState(enum.IntEnum):
    WAITING = 0
    STARTING = 1
    GENERATING = 2
    ABORTING = 3
    STOPPED = 4


class UdpDataGenerator:
    def __init__(
        self: UdpDataGenerator,
        environment: Dict[str, Any],
        scanlen: int,
        udpgen_extra_args: List[str],
        logger: logging.Logger,
    ) -> None:
        self.environment = environment
        self.scanlen = scanlen
        self.udpgen_extra_args = udpgen_extra_args
        self.logger = logger
        self.udp_data_thread: Optional[threading.Thread] = None
        self._state = _GeneratingState.WAITING

        # threading lock.  This needs to a reentrant lock
        self._rlock = threading.RLock()

        self._process: Optional[subprocess.Popen] = None
        self._abort_evt = threading.Event()
        self._state_change_condvar = threading.Condition(lock=self._rlock)

    def __del__(self: UdpDataGenerator) -> None:
        """Handle instance being deleted."""
        self.abort()

    def is_starting(self: UdpDataGenerator) -> bool:
        with self._rlock:
            return self._state == _GeneratingState.STARTING

    def is_generating(self: UdpDataGenerator) -> bool:
        with self._rlock:
            return self._state == _GeneratingState.GENERATING

    def is_aborting(self: UdpDataGenerator) -> bool:
        with self._rlock:
            return self._state == _GeneratingState.ABORTING

    def is_stopped(self: UdpDataGenerator) -> bool:
        with self._rlock:
            return self._state == _GeneratingState.STOPPED

    def wait_for(
        self: UdpDataGenerator, predicate: Callable[..., bool], timeout: float | None = None
    ) -> None:
        with self._state_change_condvar:
            self._state_change_condvar.wait_for(predicate, timeout=timeout)

    def abort(self: UdpDataGenerator) -> None:
        """Abort sending data if its running."""
        with self._rlock:
            # we haven't event started
            if self._state == _GeneratingState.WAITING:
                return

            if self.is_generating() or self.is_starting():
                assert not self._abort_evt.is_set(), "Abort evt set but should not have been"
                self._set_state(state=_GeneratingState.ABORTING)
                self._abort_evt.set()

        self.wait_for(self.is_stopped)

    def _set_state(self: UdpDataGenerator, state: _GeneratingState) -> None:
        with self._state_change_condvar:
            self._state = state
            self._state_change_condvar.notify_all()

    def _generate_config_file(
        self: UdpDataGenerator,
        file_handler: TextIO,
    ) -> None:
        """Generate config file from template."""
        import pathlib

        from jinja2 import Environment, FileSystemLoader

        templates_path = pathlib.Path(__file__).parent / "templates"

        env = Environment(loader=FileSystemLoader(templates_path))
        template = env.get_template("config.txt.j2")

        output = template.render(**self.environment)
        self.logger.info(f"Generated Output file:\n{output}")

        file_handler.write(output)
        # ensure the data is flushed
        file_handler.flush()
        self.logger.info(f"Data written to {file_handler.name}")

    def _read_stdout(self: UdpDataGenerator) -> Any:
        assert self._process is not None
        if self._process.stdout:
            stdout = self._process.stdout.readline()
        else:
            stdout = None
        return stdout

    def _read_stderr(self: UdpDataGenerator) -> Any:
        assert self._process is not None
        if self._process.stderr:
            stderr = self._process.stderr.readline()
        else:
            stderr = None
        return stderr

    def _check_stop_logging_output(self: UdpDataGenerator) -> bool:
        assert self._process is not None
        return not self.is_generating() or self._process.returncode is not None

    def _stream_subprocess_output_to_log(self: UdpDataGenerator) -> None:
        """Stream outputs from process."""

        try:
            assert self._process is not None
            while True:
                stdout = self._read_stdout()
                stderr = self._read_stderr()

                if self._check_stop_logging_output():
                    # Break logging loop when subprocess completes
                    break

                if stdout:
                    self.logger.info(f"[UDPGEN] {str(stdout)}")
                if stderr:
                    self.logger.error(f"[UDPGEN] {str(stderr)}")

                if stdout is None and stderr is None:
                    self.logger.error("[UDPGEN] stdout and stderr is None")

        except AttributeError:
            # process may be set to None from another thread this is okay.
            if self._process is None:
                pass
            else:
                raise

    def generate_udp_data(self: UdpDataGenerator) -> None:
        """Generate UDP data.

        This will launch a background thread that will handle an external
        process that does the work for sending udp data.
        """
        assert self.udp_data_thread is None, "UDP Generator already generating data"

        self.udp_data_thread = udp_data_thread = threading.Thread(
            target=self._generate_udp_data_background,
        )
        udp_data_thread.start()

        self.wait_for(self.is_generating, timeout=1.0)

        # The UDP generator process waits for a second boundary
        time.sleep(1.0)

    def _generate_udp_data_background(
        self: UdpDataGenerator,
    ) -> None:
        """Generate UDP data in the background.

        This will first generate a config file and then launch a subprocess that uses
        ska_pst_recv_udpgen to send bytes to the RECV.CORE process.
        """
        import random

        try:
            self.logger.info("Starting to create UDP data.")
            self._set_state(state=_GeneratingState.STARTING)

            rand_suff = random.randint(1000, 10000)
            scan_id = self.environment["scan_id"]
            beam_id = self.environment["beam_id"]

            filename = f"/tmp/config_scan_{scan_id}_beam_{beam_id}_{rand_suff}.txt"
            self.logger.info(f"Creating config file: {filename}")

            with open(filename, mode="w+") as fh:
                self._generate_config_file(file_handler=fh)

            self.logger.debug(f"scanlen: {self.scanlen}")
            self.logger.debug(f"udpgen_extra_args: {self.udpgen_extra_args}")
            cmd = ["ska_pst_recv_udpgen", "-t", str(self.scanlen), fh.name, "-r", "-1.0"]
            cmd = [*cmd, *self.udpgen_extra_args]

            self.logger.info(f"generate_udp_data cmd={cmd}")
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self._set_state(state=_GeneratingState.GENERATING)
            self.logger.info(f"Process {self._process.pid} has started")

            t = threading.Thread(target=self._stream_subprocess_output_to_log)
            t.setDaemon(True)
            t.start()

            try:
                if self._abort_evt.wait(timeout=self.scanlen):
                    self.logger.info("Abort event has been set.  Trying to terminate scan.")
                    self._process.terminate()
            except TimeoutError:
                pass

            self._process.wait()
            self._set_state(state=_GeneratingState.STOPPED)
            self.logger.info(f"Process return code: {self._process.returncode}")
        except Exception:
            self.logger.exception("Error in trying to create UDP data.", exc_info=True)
            self._set_state(state=_GeneratingState.STOPPED)
            raise

    def wait_for_end_of_data(self: UdpDataGenerator) -> None:
        """Wait until all the data has been sent."""
        self.wait_for(self.is_stopped, timeout=2 * self.scanlen)
