# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""This module contains the pytest tests the UDP Data Generator File."""

from __future__ import annotations

import pathlib
import random
import tempfile
from typing import Any, Generator

import pytest

from ska_pst_testutils.udp_gen import (
    GaussianNoiseConfig,
    SineWaveConfig,
    SquareWaveConfig,
    UdpDataGenerator,
    create_udp_data_generator,
)


def _read_config_file(file_path: pathlib.Path) -> dict:
    values: dict = {}
    with open(file_path, "rt") as f:
        for line in f.readlines():
            # ignore empty lines
            line = line.strip()
            if line == "":
                continue

            if line.startswith("#"):
                # this is a comment, so continue
                continue

            try:
                [key, value] = line.split(maxsplit=1)
            except ValueError:
                key = line
                value = None

            values[key] = value

    return values


@pytest.fixture
def config_file_path(
    scan_id: int,
) -> Generator[pathlib.Path, None, None]:
    """Generate a file path for the expected output config file."""
    file_path = pathlib.Path(tempfile.gettempdir()) / f"{scan_id}.txt"
    yield file_path
    if file_path.exists():
        file_path.unlink()


@pytest.fixture
def sinusoid_freq() -> float:
    """Generate random sinusoid_freq between [0.1, 10.0)."""
    return 9.9 * random.random() + 0.1


def test_constructing_sine_wave_generator(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    sinusoid_freq: float,
    config_file_path: pathlib.Path,
) -> None:
    """Test Sine Wave generator config file is correct."""
    generator: UdpDataGenerator = create_udp_data_generator(
        scan_id=scan_id,
        scanlen=scanlen,
        channel_block_configuration=channel_block_configuration,
        data_generator="Sine",
        generator_params=SineWaveConfig(sinusoid_freq=sinusoid_freq),
        scan_resources={},
    )

    assert "data_generator" in generator.environment
    assert "sinusoid_freq" in generator.environment
    assert generator.environment["sinusoid_freq"] == sinusoid_freq

    assert not config_file_path.exists(), f"Expected {config_file_path} not to exist"

    with open(config_file_path, "w+") as f:
        generator._generate_config_file(f)

    assert config_file_path.exists(), f"Expected {config_file_path} not to exist"
    values = _read_config_file(file_path=config_file_path)

    assert "DATA_GENERATOR" in values
    assert "SINUSOID_FREQ" in values

    assert values["DATA_GENERATOR"] == "Sine"
    assert values["SINUSOID_FREQ"] == str(sinusoid_freq)


def test_constructing_sine_wave_generator_when_no_sinusoid_freq_given(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
) -> None:
    """Test Sine Wave generator fails validation if sinusoid_freq is not provided."""
    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="Sine",
            scan_resources={},
        )

    assert "Expected 'sinusoid_freq' set when data_generator is 'Sine'" in str(excinfo.value)


def test_constructing_sine_wave_generator_when_sinusoid_freq_is_not_numeric(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
) -> None:
    """Test Sine Wave generator fails validation if sinusoid_freq is not numeric."""
    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="Sine",
            sinusoid_freq="this is invalid",
            scan_resources={},
        )

    assert "Expected 'sinusoid_freq' to be a float when data_generator is 'Sine'" in str(excinfo.value)


def test_constructing_gaussian_noise_generator_default_values(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    config_file_path: pathlib.Path,
) -> None:
    """Test Gaussian Noise generator allows all values to be default."""
    generator: UdpDataGenerator = create_udp_data_generator(
        scan_id=scan_id,
        scanlen=scanlen,
        channel_block_configuration=channel_block_configuration,
        data_generator="GaussianNoise",
        scan_resources={},
    )

    assert "data_generator" in generator.environment

    assert not config_file_path.exists(), f"Expected {config_file_path} not to exist"

    with open(config_file_path, "w+") as f:
        generator._generate_config_file(f)

    assert config_file_path.exists(), f"Expected {config_file_path} not to exist"
    values = _read_config_file(file_path=config_file_path)

    assert "DATA_GENERATOR" in values

    assert values["DATA_GENERATOR"] == "GaussianNoise"
    assert "NORMAL_DIST_MEAN" not in values
    assert "NORMAL_DIST_STDDEV" not in values
    assert "NORMAL_DIST_RED_STDDEV" not in values


@pytest.mark.parametrize(
    "param_key, param_value",
    [
        ("normal_dist_mean", 1.0),
        ("normal_dist_stddev", 25.0),
        ("normal_dist_red_stddev", 0.1),
    ],
)
def test_constructing_gaussian_noise_generator(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    config_file_path: pathlib.Path,
    param_key: str,
    param_value: Any,
) -> None:
    """Test Gaussian Noise generator with valid values."""
    generator_params = GaussianNoiseConfig(**{param_key: param_value})

    generator: UdpDataGenerator = create_udp_data_generator(
        scan_id=scan_id,
        scanlen=scanlen,
        channel_block_configuration=channel_block_configuration,
        data_generator="GaussianNoise",
        generator_params=generator_params,
        scan_resources={},
    )

    assert "data_generator" in generator.environment
    assert param_key in generator.environment
    assert generator.environment[param_key] == param_value

    assert not config_file_path.exists(), f"Expected {config_file_path} not to exist"

    with open(config_file_path, "w+") as f:
        generator._generate_config_file(f)

    assert config_file_path.exists(), f"Expected {config_file_path} not to exist"
    values = _read_config_file(file_path=config_file_path)

    assert "DATA_GENERATOR" in values

    assert values["DATA_GENERATOR"] == "GaussianNoise"
    assert values[param_key.upper()] == str(param_value)


@pytest.mark.parametrize(
    "param_key, param_value",
    [
        ("normal_dist_mean", "this is really mean"),
        ("normal_dist_stddev", "this is not a stddev"),
        ("normal_dist_red_stddev", "im seeing red"),
    ],
)
def test_constructing_gaussian_noise_generator_fails_validation_for_non_numeric_values(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    param_key: str,
    param_value: Any,
) -> None:
    """Test Gaussian Noise generator with not numeric values."""
    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="GaussianNoise",
            scan_resources={},
            **{param_key: param_value},
        )

    assert f"Expected '{param_key}' to be a float when data_generator is 'GaussianNoise'" in str(
        excinfo.value
    )


@pytest.mark.parametrize(
    "param_key, param_value",
    [
        ("normal_dist_stddev", 0.0),
        ("normal_dist_red_stddev", -1.0),
    ],
)
def test_constructing_gaussian_noise_generator_fails_validation_for_stddev_zero_or_below(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    param_key: str,
    param_value: Any,
) -> None:
    """Test Gaussian Noise generator with not numeric values."""
    generator_params = GaussianNoiseConfig(**{param_key: param_value})

    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="GaussianNoise",
            generator_params=generator_params,
            scan_resources={},
        )

    assert f"Expected '{param_key}' to be greater than 0.0 when data_generator is 'GaussianNoise'" in str(
        excinfo.value
    )


@pytest.mark.parametrize(
    "param_key, param_value",
    [
        ("cal_off_intensity", 1.0),
        ("cal_on_intensity", 2.0),
        ("cal_on_pol_0_intensity", 3.0),
        ("cal_on_pol_1_intensity", 6.0),
        ("cal_duty_cycle", 0.5),
        ("calfreq", 42.0),
    ],
)
def test_constructing_square_wave_generator(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    config_file_path: pathlib.Path,
    param_key: str,
    param_value: Any,
) -> None:
    """Test Square Wave generator for valid value."""
    generator_params = SquareWaveConfig(**{param_key: param_value})

    generator: UdpDataGenerator = create_udp_data_generator(
        scan_id=scan_id,
        scanlen=scanlen,
        channel_block_configuration=channel_block_configuration,
        data_generator="SquareWave",
        generator_params=generator_params,
        scan_resources={},
    )

    assert "data_generator" in generator.environment

    assert not config_file_path.exists(), f"Expected {config_file_path} not to exist"

    with open(config_file_path, "w+") as f:
        generator._generate_config_file(f)

    assert config_file_path.exists(), f"Expected {config_file_path} not to exist"
    values = _read_config_file(file_path=config_file_path)

    assert "DATA_GENERATOR" in values

    assert values["DATA_GENERATOR"] == "SquareWave"
    assert values[param_key.upper()] == str(param_value)


@pytest.mark.parametrize(
    "param_key, param_value, paired_param_key, paired_param_value",
    [
        ("cal_on_chan_0_intensity", 1.0, "cal_on_chan_n_intensity", 2.0),
        ("cal_on_pol_0_chan_0_intensity", 2.0, "cal_on_pol_0_chan_n_intensity", 4.0),
        ("cal_on_pol_1_chan_0_intensity", 3.0, "cal_on_pol_1_chan_n_intensity", 6.0),
    ],
)
def test_constructing_square_wave_generator_when_paired_value_present(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    config_file_path: pathlib.Path,
    param_key: str,
    param_value: Any,
    paired_param_key: str,
    paired_param_value: Any,
) -> None:
    """Test Square Wave generator for valid value when the required paired key/value is present."""
    generator_params = SquareWaveConfig(**{param_key: param_value, paired_param_key: paired_param_value})

    generator: UdpDataGenerator = create_udp_data_generator(
        scan_id=scan_id,
        scanlen=scanlen,
        channel_block_configuration=channel_block_configuration,
        data_generator="SquareWave",
        generator_params=generator_params,
        scan_resources={},
    )

    assert "data_generator" in generator.environment

    assert not config_file_path.exists(), f"Expected {config_file_path} not to exist"

    with open(config_file_path, "w+") as f:
        generator._generate_config_file(f)

    assert config_file_path.exists(), f"Expected {config_file_path} not to exist"
    values = _read_config_file(file_path=config_file_path)

    assert "DATA_GENERATOR" in values

    assert values["DATA_GENERATOR"] == "SquareWave"
    assert values[param_key.upper()] == str(param_value)
    assert values[paired_param_key.upper()] == str(paired_param_value)


def test_constructing_square_wave_generator_default_values(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    config_file_path: pathlib.Path,
) -> None:
    """Test Square Wave generator allows all values to be default."""
    generator: UdpDataGenerator = create_udp_data_generator(
        scan_id=scan_id,
        scanlen=scanlen,
        channel_block_configuration=channel_block_configuration,
        data_generator="SquareWave",
        generator_params=SquareWaveConfig(),
        scan_resources={},
    )

    assert "data_generator" in generator.environment

    assert not config_file_path.exists(), f"Expected {config_file_path} not to exist"

    with open(config_file_path, "w+") as f:
        generator._generate_config_file(f)

    assert config_file_path.exists(), f"Expected {config_file_path} not to exist"
    values = _read_config_file(file_path=config_file_path)

    assert "DATA_GENERATOR" in values

    assert values["DATA_GENERATOR"] == "SquareWave"
    assert "CAL_OFF_INTENSITY" not in values
    assert "CAL_ON_INTENSITY" not in values
    assert "CAL_ON_POL_0_INTENSITY" not in values
    assert "CAL_ON_POL_1_INTENSITY" not in values
    assert "CAL_ON_CHAN_0_INTENSITY" not in values
    assert "CAL_ON_CHAN_N_INTENSITY" not in values
    assert "CAL_ON_POL_0_CHAN_0_INTENSITY" not in values
    assert "CAL_ON_POL_0_CHAN_N_INTENSITY" not in values
    assert "CAL_ON_POL_1_CHAN_0_INTENSITY" not in values
    assert "CAL_ON_POL_1_CHAN_N_INTENSITY" not in values
    assert "CAL_DUTY_CYCLE" not in values
    assert "CALFREQ" not in values


@pytest.mark.parametrize(
    "param_key, param_value",
    [
        ("cal_off_intensity", "cal_off_intensity is not a number"),
        ("cal_on_intensity", "cal_on_intensity is not a number"),
        ("cal_on_pol_0_intensity", "cal_on_pol_0_intensity is not a number"),
        ("cal_on_pol_1_intensity", "cal_on_pol_1_intensity is not a number"),
        ("cal_on_chan_0_intensity", "cal_on_chan_0_intensity is not a number"),
        ("cal_on_pol_1_chan_n_intensity", "cal_on_pol_1_chan_n_intensity is not a number"),
        ("cal_duty_cycle", "cal_duty_cycle is not a number"),
        ("calfreq", "calfreq is not a number"),
    ],
)
def test_constructing_square_wave_generator_fails_validation_for_non_numeric_values(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    param_key: str,
    param_value: Any,
) -> None:
    """Test Square Wave generator with not numeric values."""
    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="SquareWave",
            scan_resources={},
            **{param_key: param_value},
        )

    assert f"Expected '{param_key}' to be a float when data_generator is 'SquareWave'" in str(excinfo.value)


@pytest.mark.parametrize(
    "param_key, param_value, required_paired_key",
    [
        ("cal_on_chan_0_intensity", 1.0, "cal_on_chan_n_intensity"),
        ("cal_on_chan_n_intensity", 2.0, "cal_on_chan_0_intensity"),
        ("cal_on_pol_0_chan_0_intensity", 4.0, "cal_on_pol_0_chan_n_intensity"),
        ("cal_on_pol_0_chan_n_intensity", 8.0, "cal_on_pol_0_chan_0_intensity"),
        ("cal_on_pol_1_chan_0_intensity", 16.0, "cal_on_pol_1_chan_n_intensity"),
        ("cal_on_pol_1_chan_n_intensity", 32.0, "cal_on_pol_1_chan_0_intensity"),
    ],
)
def test_constructing_square_wave_generator_asserts_other_parameter_is_required(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    param_key: str,
    param_value: Any,
    required_paired_key: str,
) -> None:
    """Test Square Wave generator asserts other parameter is required."""
    generator_params = SquareWaveConfig(**{param_key: param_value})

    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="SquareWave",
            generator_params=generator_params,
            scan_resources={},
        )

    assert f"Expected '{required_paired_key}' set when data_generator is 'SquareWave'" in str(excinfo.value)


@pytest.mark.parametrize(
    "param_key, param_value, message",
    [
        ("cal_duty_cycle", -0.1, "to be within following range (0.0, 1.0)"),
        ("cal_duty_cycle", 0.0, "to be within following range (0.0, 1.0)"),
        ("cal_duty_cycle", 1.0, "to be within following range (0.0, 1.0)"),
        ("cal_duty_cycle", 1.1, "to be within following range (0.0, 1.0)"),
        ("calfreq", 0.0, "to be greater than 0.0"),
    ],
)
def test_constructing_square_wave_generator_asserts_min_max_values(
    scan_id: int,
    scanlen: int,
    channel_block_configuration: dict,
    param_key: str,
    param_value: Any,
    message: str,
) -> None:
    """Test Square Wave generator asserts min/max values."""
    generator_params = SquareWaveConfig(**{param_key: param_value})

    with pytest.raises(AssertionError) as excinfo:
        create_udp_data_generator(
            scan_id=scan_id,
            scanlen=scanlen,
            channel_block_configuration=channel_block_configuration,
            data_generator="SquareWave",
            generator_params=generator_params,
            scan_resources={},
        )

    assert f"Expected '{param_key}' {message} when data_generator is 'SquareWave'" in str(excinfo.value)
