# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module for providing helper functions and classes for generating test UDP data."""

from __future__ import annotations

import dataclasses
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


def _assert_required(key: str, /, *args: Any, data_generator: str, **kwargs: Any) -> None:
    assert key in kwargs, f"Expected '{key}' set when data_generator is '{data_generator}'"


def _assert_float(
    key: str, /, *args: Any, data_generator: str, required: bool = False, **kwargs: Any
) -> None:
    if required:
        _assert_required(key, data_generator=data_generator, **kwargs)
    if key in kwargs:
        assert isinstance(
            kwargs[key], (int, float)
        ), f"Expected '{key}' to be a float when data_generator is '{data_generator}'"


def _assert_min_value(
    key: str, /, *args: Any, data_generator: str, min_value: float, inclusive: bool = True, **kwargs: Any
) -> None:
    if key in kwargs:
        value = float(kwargs[key])
        if inclusive:
            assert min_value <= value, (
                f"Expected '{key}' to be greater or equal to {min_value} "
                f"when data_generator is '{data_generator}'"
            )
        else:
            assert (
                min_value < value
            ), f"Expected '{key}' to be greater than {min_value} when data_generator is '{data_generator}'"


def _validate_sine_wave_generator(
    **kwargs: Any,
) -> None:
    _assert_float("sinusoid_freq", required=True, **kwargs)


def _validate_gaussian_noise_generator(
    **kwargs: Any,
) -> None:
    _assert_float("normal_dist_mean", required=False, **kwargs)
    _assert_float("normal_dist_stddev", required=False, **kwargs)
    _assert_min_value("normal_dist_stddev", min_value=0.0, inclusive=False, **kwargs)
    _assert_float("normal_dist_red_stddev", required=False, **kwargs)
    _assert_min_value("normal_dist_red_stddev", min_value=0.0, inclusive=False, **kwargs)


def _validate_square_wave_generator(
    **kwargs: Any,
) -> None:
    _assert_float("cal_off_intensity", **kwargs)
    _assert_float("cal_on_intensity", **kwargs)
    _assert_float("cal_on_pol_0_intensity", **kwargs)
    _assert_float("cal_on_pol_1_intensity", **kwargs)
    _assert_float("cal_on_chan_0_intensity", **kwargs)
    _assert_float("cal_on_chan_n_intensity", **kwargs)
    _assert_float("cal_on_pol_0_chan_0_intensity", **kwargs)
    _assert_float("cal_on_pol_0_chan_n_intensity", **kwargs)
    _assert_float("cal_on_pol_1_chan_0_intensity", **kwargs)
    _assert_float("cal_on_pol_1_chan_n_intensity", **kwargs)
    _assert_float("cal_duty_cycle", **kwargs)
    _assert_float("calfreq", **kwargs)

    if "cal_on_chan_0_intensity" in kwargs:
        _assert_required("cal_on_chan_n_intensity", **kwargs)

    if "cal_on_chan_n_intensity" in kwargs:
        _assert_required("cal_on_chan_0_intensity", **kwargs)

    if "cal_on_pol_0_chan_0_intensity" in kwargs:
        _assert_required("cal_on_pol_0_chan_n_intensity", **kwargs)

    if "cal_on_pol_0_chan_n_intensity" in kwargs:
        _assert_required("cal_on_pol_0_chan_0_intensity", **kwargs)

    if "cal_on_pol_1_chan_0_intensity" in kwargs:
        _assert_required("cal_on_pol_1_chan_n_intensity", **kwargs)

    if "cal_on_pol_1_chan_n_intensity" in kwargs:
        _assert_required("cal_on_pol_1_chan_0_intensity", **kwargs)

    if "cal_duty_cycle" in kwargs:
        cal_duty_cycle: float = kwargs["cal_duty_cycle"]
        assert 0.0 < cal_duty_cycle < 1.0, (
            "Expected 'cal_duty_cycle' to be within following "
            "range (0.0, 1.0) when data_generator is 'SquareWave'"
        )

    if "calfreq" in kwargs:
        _assert_min_value("calfreq", min_value=0.0, inclusive=False, **kwargs)


VALIDATORS: Dict[str, Callable] = {
    "Sine": _validate_sine_wave_generator,
    "GaussianNoise": _validate_gaussian_noise_generator,
    "SquareWave": _validate_square_wave_generator,
    "Random": lambda *args, **kwargs: None,
}


@dataclasses.dataclass(kw_only=True)
class SineWaveConfig:
    """Config data class for the Sine wave data generator."""

    sinusoid_freq: float
    """The frequency of the sine wave."""


@dataclasses.dataclass(kw_only=True)
class GaussianNoiseConfig:
    """Config data class for the GaussianNoise data generator."""

    normal_dist_mean: float | None = None
    """The mean for the normal distribution.

    If not set this will default to 0.0.
    """

    normal_dist_stddev: float | None = None
    """The standard deviation of normal distribution.

    If not set this will default to 10.0.
    """

    normal_dist_red_stddev: float | None = None
    """The standard deviation of a red noise process.

    If not set, or set to 0.0, there will be no red noise applied.
    """


@dataclasses.dataclass(kw_only=True)
class SquareWaveConfig:
    """Config data class for the SquareWave data generator.

    If any one of the above CHAN_0 intensities is specified, then the matching CHAN_N intensity must
    also be specified. Each CHAN_0,CHAN_N pair defines an intensity gradient that will be applied to
    all frequency channels. If any intensity (in any polarization or frequency channel) is multiply
    defined, then the intensity configuration parameters that appear later in the above list will
    override any configuration set by parameters listed earlier.
    """

    cal_off_intensity: float | None = None
    """The off-pulse intensity for all polarizations and frequency channels."""

    cal_on_intensity: float | None = None
    """The on-pulse intensity for all polarizations and frequency channels."""

    cal_on_pol_0_intensity: float | None = None
    """The on-pulse intensity for polarization 0 and all frequency channels."""

    cal_on_pol_1_intensity: float | None = None
    """The on-pulse intensity for polarization 1 and all frequency channels."""

    cal_on_chan_0_intensity: float | None = None
    """The on-pulse intensity for all polarizations at frequency channel zero."""

    cal_on_chan_n_intensity: float | None = None
    """The on-pulse intensity for all polarizations at the number of frequency channels."""

    cal_on_pol_0_chan_0_intensity: float | None = None
    """The on-pulse intensity for polarization 0 at frequency channel zero."""

    cal_on_pol_0_chan_n_intensity: float | None = None
    """The on-pulse intensity for polarization 0 at the number of frequency channels."""

    cal_on_pol_1_chan_0_intensity: float | None = None
    """The on-pulse intensity for polarization 1 at frequency channel zero."""

    cal_on_pol_1_chan_n_intensity: float | None = None
    """The on-pulse intensity for polarization 1 at the number of frequency channels"""

    cal_duty_cycle: float | None = None
    """The fraction of period in the on-pulse state.

    If not set the default value is 0.5.
    """

    calfreq: float | None = None
    """The frequency of square wave (inverse of period) in Hz"""


def create_udp_data_generator(
    scan_resources: Dict[str, Any],
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    data_generator: str | None = None,
    generator_params: SineWaveConfig | GaussianNoiseConfig | SquareWaveConfig | None = None,
    udpgen_extra_args: List[str] | None = None,
    logger: logging.Logger | None = None,
    **kwargs: Any,
) -> UdpDataGenerator:
    """Create instance of a UpdDataGenerator.

    This is a utility method to help with creating an instance of
    a UpdDataGenerator object. This method should be preferred
    over calling the constructor directly as this will validate
    extra parameters needed for different types of data generators.

    This method handles the following types of generators:

        * Random - the default, just sends uniform random data.
        * GaussianNoise - sends normally distributed data given
          as mean and standard deviation, along with optional
          red noise parameters.
        * Sine - a sine wave generator with a given frequency.
        * SquareWave - sends a square wave signal with configurable
          duty cycle, calfrequency

    :param scan_resources: parameters relating to the resources returned
        from calling :py:meth:`ScanConfigGenerator.calculate_resources`
    :type scan_resources: Dict[str, Any]
    :param scan_id: the Scan ID
    :type scan_id: int
    :param scanlen: the scan length in seconds.
    :type scanlen: int
    :param channel_block_configuration: details about where to send UDP
        data to. This can be retrieved from the BEAM.MGMT TANGO device's
        :py:attr:`channelBlockConfiguration` after a scan has been configured.
    :type channel_block_configuration: dict
    :param data_generator: the name of the data generate, defaults to None.
        Valid values are listed above.
    :type data_generator: str | None, optional
    :param data_generator: the name of the data generate, defaults to None.
        Valid values are listed above.
    :type data_generator: str | None, optional
    :param generator_params: generator specific parameters, defaults to None.
        These are type safe generator parameters that should be preferred rather than
        using the ``kwargs`` of the function.
    :type generator_params: SineWaveConfig | GaussianNoiseConfig | SquareWaveConfig | None, optional
    :param udpgen_extra_args: extra parameters that should be sent to the
        ``ska_pst_recv_udpgen`` executable, defaults to None
    :type udpgen_extra_args: List[str] | None, optional
    :param logger: the logger to within the generator, defaults to None
    :type logger: logging.Logger | None, optional
    :return: an instance of the UdpDataGenerator
    :rtype: UdpDataGenerator
    """
    data_host = channel_block_configuration["channel_blocks"][0]["destination_host"]
    data_port = channel_block_configuration["channel_blocks"][0]["destination_port"]

    params = {} if generator_params is None else dataclasses.asdict(generator_params)
    params = {
        # remove values with None
        **{k: v for (k, v) in params.items() if v is not None},
        **kwargs,
    }

    if data_generator is not None:
        assert data_generator in VALIDATORS, f"Unknown data generator {data_generator}"
        VALIDATORS[data_generator](data_generator=data_generator, **params)

    environment = {
        **scan_resources,
        "data_host": data_host,
        "data_port": data_port,
        "scan_id": scan_id,
        "scanlen_max": scanlen,
        "data_generator": data_generator,
        **params,
    }

    return UdpDataGenerator(
        environment=environment,
        scanlen=scanlen,
        udpgen_extra_args=udpgen_extra_args,
        logger=logger,
    )


class UdpDataGenerator:
    """Class used to abstract away generating of UDP data.

    This class should be used to simulate UDP data is sent to PST
    when there is no upstream CBF data.

    This class is configured with an environment that can then generate
    a config file for the `ska_pst_recv_udpgen` command.

    Creating an instance of this does not do anything, the call to
    `generate_udp_data` is needed. Which will in turn run a background
    process to generate the data without blocking the client.  If the
    client wants to wait for the data to have been completely sent they
    should call `wait_for_end_of_data`.
    """

    def __init__(
        self: UdpDataGenerator,
        environment: Dict[str, Any],
        scanlen: int,
        udpgen_extra_args: List[str] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Create instance of UDP data generator.

        :param environment: the environment for the UDP data generator.
            This should include the scan configuration, calculated resources
            and any overridden values specific for this instance.
        :param scanlen: the length, in seconds, for how long to generate data
            for.
        :param udpgen_extra_args: extra command values to pass to the
            `ska_pst_recv_udpgen`, such the data shape or to induce invalid
            or dropped packets.
        :param logger: the logger to use for this instance.
        """
        self.environment = environment
        self.scanlen = scanlen
        self.udpgen_extra_args = udpgen_extra_args if udpgen_extra_args is not None else []
        self.logger = logger or logging.getLogger(__name__)
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
        """Check if UDP generator is starting up.

        The generator has been requested to start generating but
        hasn't started to generate the data.  This is different
        to `is_generating` as there is background processing happening
        and is used to avoid calling the generate method twice.
        """
        with self._rlock:
            return self._state == _GeneratingState.STARTING

    def is_generating(self: UdpDataGenerator) -> bool:
        """Check if UDP generator is generating data."""
        with self._rlock:
            return self._state == _GeneratingState.GENERATING

    def is_aborting(self: UdpDataGenerator) -> bool:
        """Check if UDP generator is aborting."""
        with self._rlock:
            return self._state == _GeneratingState.ABORTING

    def is_stopped(self: UdpDataGenerator) -> bool:
        """Check if UDP generator has stopped generating data."""
        with self._rlock:
            return self._state == _GeneratingState.STOPPED

    def wait_for(
        self: UdpDataGenerator,
        predicate: Callable[..., bool],
        timeout: float | None = None,
    ) -> None:
        """Wait until a given condition is met.

        This method waits for changes of the state of the data generator and
        then checks the predicate to see if it should return.

        This method can take an optional timeout to avoid blocking indefinitely.

        :param predicate: the predicate to wait against.
        :param timeout: the amount of time to wait for the condition to be met
            else this returns.
        """
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
            cmd = [
                "ska_pst_recv_udpgen",
                "-t",
                str(self.scanlen),
                fh.name,
                "-r",
                "-1.0",
            ]
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
