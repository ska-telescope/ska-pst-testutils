# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module to asserting statistics."""

from __future__ import annotations

import dataclasses
from typing import List

import numpy as np
import pandas as pd


@dataclasses.dataclass
class SampleStatistics:
    """Data class that models the a statistics of a sample.

    :ivar mean: the mean of the sample
    :vartype mean: float
    :ivar variance: the variance of the sample
    :vartype variance: float
    :ivar num_samples: the number of samples used to calculate the statistics
    :vartype num_samples: float
    """

    mean: float
    variance: float
    num_samples: int


def assert_statistics(
    population_mean: float,
    population_var: float,
    sample_stats: SampleStatistics,
    tolerance: float = 6.0,
) -> None:
    """Assert that sample mean and var are within a given tolerance of population stats.

    :param population_mean: the mean of the population
    :type population_mean: float
    :param population_var: the variance of the population
    :type population_var: float
    :param sample_mean: the mean of the sample
    :type sample_mean: float
    :param sample_var: the variance of the sample
    :type sample_var: float
    :param num_samples: the sample size
    :type num_samples: int
    :param tolerance: the number of sigma to allow being away from population value, defaults to 6.0
    :type tolerance: float, optional
    :param statistics_type: the type of statistic to assert. Default is both mean and variance.
    :type statistics_type: StatisticType
    """
    N = sample_stats.num_samples
    S = population_var
    mu = population_mean
    # This is the 4th moment of a gaussian distribution
    mu_4 = 3.0 * S**2
    E = sample_stats.mean
    V = sample_stats.variance

    # expected variance in E
    var_e = S / N
    sigma_e = np.sqrt(var_e)

    # expected variance in V
    var_v = (mu_4 - (N - 3) / (N - 1) * S**2) / N
    sigma_v = np.sqrt(var_v)

    n_sigma_e = np.fabs(E - mu) / sigma_e
    n_sigma_v = np.fabs(V - S) / sigma_v

    assert n_sigma_e <= tolerance and n_sigma_v <= tolerance, (
        f"Expected sample mean ({E:0.6f}) and variance ({V:0.3f}) to be within {tolerance:0.3f} sigma"
        f" of {mu:0.6f} and {S:0.3f} respectively. n_sigma_e={n_sigma_e:0.3f}, "
        f"n_sigma_v={n_sigma_v:0.3f}"
    )


def assert_statistics_for_channels(
    channel_data: pd.DataFrame,
    population_mean: float,
    population_var: float,
    tolerance: float = 6.0,
) -> None:
    """Assert that sample mean and var are within a given tolerance of population stats for each channel.

    :param channel_data: a data frame with statistics split by channel. This must include the following
        columns: "Mean", "Var.", "Num Samples".  This should also be specific for a given polarisation
        and complex data dimension (e.g. for Pol A real data).
    :type channel_data: pd.DataFrame
    :param population_mean: the mean of the population
    :type population_mean: float
    :param population_var: the variance of the population
    :type population_var: float
    :param tolerance: the number of sigma to allow being away from population value, defaults to 6.0
    :type tolerance: float, optional
    :param statistics_type: the type of statistic to assert. Default is both mean and variance.
    :type statistics_type: StatisticType
    """
    errors: List[str] = []
    for (_, (sample_mean, sample_var, num_samples)) in channel_data[
        ["Mean", "Var.", "Num. Samples"]
    ].iterrows():
        try:
            sample_stats = SampleStatistics(
                num_samples=num_samples,
                mean=sample_mean,
                variance=sample_var,
            )
            assert_statistics(
                population_mean=population_mean,
                population_var=population_var,
                sample_stats=sample_stats,
                tolerance=tolerance,
            )
        except AssertionError as e:
            errors.append(str(e))

    assert len(errors) == 0, f"Expected no errors. Error messages = {errors}"
