# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module used to analyse that bandpass of a file."""

import dataclasses
import sys
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np


@dataclasses.dataclass
class Maxima:
    """Data class that represents the maxima of a polarisation.

    :ivar channel: the channel number which has the maximum value.
    :vartype channel: int
    :ivar value: the value of the maxima.
    :vartype value: float
    """

    channel: int
    value: float


def unpack_data_file(data_file: str) -> Dict[str, np.ndarray]:
    """Unpack the raw binary data file into numpy arrays."""
    with open(data_file, "rb") as fptr:
        nchan = np.fromfile(fptr, dtype=np.uint32, count=1)[0]
        npol = np.fromfile(fptr, dtype=np.uint32, count=1)[0]
        axes: Dict[str, np.ndarray] = {}
        axes["x"] = np.fromfile(fptr, dtype=np.float32, count=nchan)
        axes["y"] = np.fromfile(fptr, dtype=np.float32, count=npol * nchan).reshape((npol, nchan))
        return axes


def validate_maxima_in_channel(
    axes: Dict[str, np.ndarray], expected_maxima_channel: int, db_limit: float = -40
) -> None:
    """Validate the maxima is in the correct channel.

    This checks that the maxima of the power is in the correct channel
    and the other channels are below the db_limit
    """
    npol = len(axes["y"])
    nchan = len(axes["x"])

    maxima = get_maxima(axes)
    db = get_db(axes, True)
    for ipol in range(npol):
        if maxima[ipol].channel != expected_maxima_channel:
            print(
                (
                    f"ERROR: maxima in polarisation {ipol} was found in channel {maxima[ipol].channel}, "
                    f"expecting {expected_maxima_channel}"
                )
            )
            sys.exit(1)
        for ichan in range(nchan):
            if ichan != expected_maxima_channel and db["y"][ipol][ichan] > db_limit:
                print(
                    (
                        f"ERROR: power in polarisation {ipol}, channel {ichan} was {db['y'][ipol][ichan]} "
                        f"which exceeded the limit of {db_limit}"
                    )
                )
                sys.exit(1)


def get_maxima(axes: Dict[str, np.ndarray]) -> Dict[int, Maxima]:
    """Find the channel number and Frequency for the maximum value in each polarisation."""
    maxima = {}
    npol = len(axes["y"])
    for ipol in range(npol):
        max_chan = int(np.argmax(axes["y"][ipol]))
        max_val = axes["y"][ipol][max_chan]
        maxima[ipol] = Maxima(channel=max_chan, value=max_val)
    return maxima


def get_db(axes: Dict[str, np.ndarray], add_noise: bool = False) -> Dict[str, np.ndarray]:
    """Convert the bandpass in the axes to dB."""
    nchan = len(axes["x"])
    npol = len(axes["y"])

    for ipol in range(npol):
        spectra = axes["y"][ipol]
        if add_noise:
            spectra = spectra + np.random.normal(1000, 5, nchan)
        maxval = np.max(spectra)
        axes["y"][ipol] = 10 * np.log10(spectra / maxval)
    return axes


def plot_bandpass(axes: Dict[str, np.ndarray], linear: bool = True) -> None:
    """Plot the bandpasses stored in the axes linearly."""
    nchan = len(axes["x"])
    npol = len(axes["y"])

    fig, axs = plt.subplots(npol, 1)
    fig.suptitle(f"Bandpass of {nchan} channels with {npol} polarisations")

    for ipol in range(npol):
        axs[ipol].plot(axes["x"], axes["y"][ipol])
        axs[ipol].set_title(f"Polarisation {ipol}")
        if linear:
            axs[ipol].set_ylabel("Uncalibrated power")
        else:
            axs[ipol].set_ylabel("Power [dB]")

    plt.xlabel("Frequency [MHz]")
    fig.tight_layout()
    plt.show()


def analyse_bandpass(
    *args: Any,
    data_file: str,
    expected_maxima_channel: int = -1,
    plot_db: bool = False,
    plot_linear: bool = False,
    **kwargs: Any,
) -> None:
    """Analyse a data file."""
    axes = unpack_data_file(data_file)
    maxima = get_maxima(axes)

    for ipol in maxima.keys():
        print(f"polarisation={ipol} max channel={maxima[ipol].channel} value={maxima[ipol].value}")

    if expected_maxima_channel >= 0:
        validate_maxima_in_channel(axes, expected_maxima_channel)
    if plot_db:
        axes = get_db(axes, True)
        plot_bandpass(axes, False)
    elif plot_linear:
        plot_bandpass(axes, True)


def main() -> None:
    """Perform analysis.

    This is the main entry into performing the bandpass analysis of a file.
    This should only be used from a command line, if using from a notebook
    then the :py:meth:`analyse` should be used.  This method will ultimately
    call that method, all this method does is parse the command line arguments.
    """
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("data_file", type=str, help="Raw data file to analyse")
    p.add_argument("--dB", dest="plot_db", action="store_true", help="Plot the bandpass in a dB scale")
    p.add_argument(
        "--linear", dest="plot_linear", action="store_true", help="Plot the bandpass in a linear scale"
    )
    p.add_argument(
        "--validate",
        type=int,
        default=-1,
        dest="expected_maxima_channel",
        help=(
            "Validate that the maxima is present in the expected channel and that all other channels "
            "are -40dB below the peak"
        ),
    )
    args = vars(p.parse_args())
    analyse_bandpass(**args)


if __name__ == "__main__":
    main()
