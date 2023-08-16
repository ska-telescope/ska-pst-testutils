# -*- coding: utf-8 -*-
#
# This file is part of the SKA PST Testutils project
#
# Distributed under the terms of the BSD 3-clause new license.
# See LICENSE for more info.

"""Module to used for analysing DSP artefacts."""

from __future__ import annotations

__all__ = [
    "DspDataAnalyser",
    "ScanFileMetadata",
]

import dataclasses
import logging
import math
import os
import pathlib
import subprocess
from typing import Any, Dict, List

from .dada_file_reader import SECONDS_PER_FILE, DadaFileReader, WeightsFileReader

BITS_PER_BYTE = 8
SIZEOF_FLOAT_IN_BYTES = 4
WEIGHTS_NBITS = 16
WEIGHTS_NDIM = 1
WEIGHTS_NPOL = 1
MILLISECS_PER_SEC = 1_000_000


@dataclasses.dataclass(kw_only=True)
class ScanFileMetadata:
    """A data class to store the metadata of a scan file."""

    name: str
    obs_offset: int
    file_number: int
    data_size: int
    file_size: int
    scan_id: int


class DspDataAnalyser:
    """Class for analysing files generated by DSP.CORE."""

    def __init__(
        self: DspDataAnalyser,
        scan_config: Dict[str, Any],
        dsp_mount: str,
        eb_id: str,
        subsystem_id: str,
        scan_id: int,
        logger: logging.Logger | None = None,
    ) -> None:
        """Create instance of DspDataAnalyser.

        :param scan_config: the configuration used for the scan.
        :param eb_id: execution block id.
        :param subsystem_id: the path indicating the subsystem.
        :param dsp_mount: the filesystem mount point where DSP's disk is.
        :param scan_id: the scan ID to analyse the data for.
        :param logger: the logger to use for the system.
        """
        self.scan_config = scan_config
        self.scan_id = scan_id
        self.eb_id = eb_id
        self.subsystem_id = subsystem_id
        self.dsp_mount = dsp_mount
        self.logger = logger or logging.getLogger(__name__)

    def get_dada_files(self: DspDataAnalyser, dada_path: pathlib.Path) -> List[pathlib.Path]:
        """Parse SCAN data path and return list of dada files."""
        return list(dada_path.glob("*.dada"))

    def check_dsp_files(
        self: DspDataAnalyser,
        dsp_subpath: str,
    ) -> None:
        r"""Analyse DSP artefacts.

        This will parse the \*.dada files mounted in $DSP_MOUNT/$EB_ID/$SUSBYSTEM_ID/$SCAN_ID/data
        and look for its pair in $DSP_MOUNT/$EB_ID/$SUSBYSTEM_ID/$SCAN_ID/weights
        """
        # Display all text files present in /tmp/ Path.
        # The scan configuration used by UDPGen should be present
        self.logger.debug(f"/tmp/*.txt: {[f for f in os.listdir('/tmp') if f.endswith('.txt')]}")
        self.logger.debug(f"{self.dsp_mount}: {os.listdir(self.dsp_mount)}")

        self.logger.debug(f"check_dsp_files.scan_config: {self.scan_config}")
        dsp_subpath = f"{self.dsp_mount}/{self.eb_id}/{self.subsystem_id}/{self.scan_id}/{dsp_subpath}"
        self.logger.debug(f"check_dsp_files.dsp_subpath: {dsp_subpath}")

        dada_files = self.get_dada_files(dada_path=pathlib.Path(dsp_subpath))
        self.logger.debug(f"check_dsp_files.data_files: {dada_files}")

        # Files must exist!
        assert dada_files != []

    def check_sinusoid_frequency(self: DspDataAnalyser, expected_frequency: float) -> None:
        r"""Analyse DSP artefacts.

        This will parse the \*.dada files mounted in $DSP_MOUNT/$EB_ID/$SUBSYSTEM_ID/$SCAN_ID
        """
        self.logger.info(f"sine_analyse.scan_config: {self.scan_config}")
        data_path = f"{self.dsp_mount}/${self.eb_id}/${self.subsystem_id}/{self.scan_id}/data"
        weights_path = f"{self.dsp_mount}/${self.eb_id}/${self.subsystem_id}/{self.scan_id}/weights"

        data_files = self.get_dada_files(dada_path=pathlib.Path(data_path))
        self.logger.info(f"sine_analyse.data_files: {data_files}")
        self.logger.info(f"sine_analyse.weights_files: {data_files}")

        analysis_stdout = []
        for data_file in data_files:
            data = f"{data_path}/{data_file}"
            weight = f"{weights_path}/{data_file}"
            cmd = ["/usr/local/bin/ska_pst_dsp_disk_sine_analyse", data, weight]

            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                output, error = proc.communicate()
                analysis_stdout.append(output.decode())
            except Exception:
                self.logger.exception("Error in checking sinusoid frequency.", exc_info=True)

        # Prevents false positives. If data_files == [], this would be []
        assert analysis_stdout != []

        for result in analysis_stdout:
            frequency_str = result.split("found at frequency=")[1].split(" ")[0]
            frequency = round(float(frequency_str), 1)
            self.logger.debug(
                (
                    f"ska_pst_dsp_disk_sine_analyse.frequency rounded off frequency={frequency} "
                    f"expected_frequency={expected_frequency}"
                )
            )
            eps = 0.1
            assert (
                abs(frequency - expected_frequency) < eps
            ), f"expected {frequency} to be within {eps} of {expected_frequency}"

    def check_contiguous_files(
        self: DspDataAnalyser,
        scanlen: float,
        calculated_resources: Dict[str, Any],
        file_type: str,
    ) -> None:
        """Check the files for the scan are contiguous."""
        tsamp = float(calculated_resources["tsamp"])
        nchan = int(calculated_resources["nchan"])
        packets_per_buffer = int(calculated_resources["packets_per_buffer"])
        bytes_per_second = float(calculated_resources["bytes_per_second"])
        resolution = int(calculated_resources["resolution"])
        nbit = int(calculated_resources["nbits"])
        ndim = int(calculated_resources["ndim"])
        npol = int(calculated_resources["npol"])
        buffer_size = packets_per_buffer * resolution

        # this is a float
        expected_size = scanlen * MILLISECS_PER_SEC * nbit * ndim * npol * nchan / (BITS_PER_BYTE * tsamp)

        # need to bytes per file
        bytes_per_file = int(math.floor(bytes_per_second * SECONDS_PER_FILE))
        if bytes_per_file % buffer_size != 0:
            # expected bytes needs to be a multiple of resolution
            bytes_per_file += buffer_size - (bytes_per_file % buffer_size)

        expected_num_files = int(math.ceil(expected_size / float(bytes_per_file)))
        num_packets_per_file = bytes_per_file // resolution

        if file_type == "weights":
            packet_nsamp = int(calculated_resources["packet_nsamp"])
            packet_nchan = int(calculated_resources["packet_nchan"])
            # idealy this should be in the config but for PST the packet_nsamp == nsamp_per_weight
            # nsamp_per_weight = int(calculated_resources["nsamp_per_weight"])
            nsamp_per_weight = packet_nsamp
            nbit = WEIGHTS_NBITS
            tsamp *= packet_nsamp
            # bytes_per_second = float(nchan * nbit * MILLISECS_PER_SEC / (BITS_PER_BYTE * tsamp))
            ndim = WEIGHTS_NDIM
            npol = WEIGHTS_NPOL
            weights_channel_stride = packet_nsamp // nsamp_per_weight * nbit // BITS_PER_BYTE
            wt_resolution = (nchan * weights_channel_stride) + (nchan // packet_nchan) * SIZEOF_FLOAT_IN_BYTES

            # bytes_per_second - should be scaled by the different resolutions
            bytes_per_second *= wt_resolution / resolution
            buffer_size = packets_per_buffer * wt_resolution
            bytes_per_file = num_packets_per_file * wt_resolution

        self.logger.info(f"nbit = {nbit}")
        self.logger.info(f"ndim = {ndim}")
        self.logger.info(f"npol = {npol}")
        self.logger.info(f"nchan = {nchan}")
        self.logger.info(f"tsamp = {tsamp}")
        self.logger.info(f"resolution = {resolution}")
        if file_type == "weights":
            self.logger.info(f"wt_resolution = {wt_resolution}")

        self.logger.info(f"buffer_size = {buffer_size}")
        self.logger.info(f"bytes_per_second = {bytes_per_second}")
        self.logger.info(f"bytes_per_file = {bytes_per_file}")
        self.logger.info(f"num_packets_per_file = {num_packets_per_file}")
        self.logger.info(f"expected_num_files = {expected_num_files}")
        self.logger.info(f"expected_size = {expected_size}")

        total_data_size: int = 0

        files_data: Dict[int, ScanFileMetadata] = {}
        file_path = (
            pathlib.Path(self.dsp_mount) / self.eb_id / self.subsystem_id / str(self.scan_id) / file_type
        )

        for f in file_path.glob("*.dada"):
            with DadaFileReader(f, logger=self.logger) as file:
                total_data_size += file.data_size
                file_data = ScanFileMetadata(
                    name=str(f.resolve()),
                    obs_offset=file.obs_offset,
                    file_number=file.file_number,
                    scan_id=file.scan_id,
                    data_size=file.data_size,
                    file_size=file.file_size,
                )
                files_data[file_data.file_number] = file_data

        self.logger.info(f"Scan data info: {files_data}")
        self.logger.info(f"Number of files: {len(files_data)}")
        self.logger.info(f"Total data size: {total_data_size}")

        assert (
            len(files_data) == expected_num_files
        ), f"expected {expected_num_files}, received {len(files_data)}"

        # need a fuzzy logic here. As RECV starts on the boundary of a second
        # we may not get a full second of data.
        recorded_scan_length = total_data_size / bytes_per_second

        self.logger.info(f"recorded {recorded_scan_length:0.6}s of data, expected around {scanlen:0.6}s")
        assert (
            abs(recorded_scan_length - scanlen) < 1.0
        ), f"recorded {recorded_scan_length}s of data, expected around {scanlen:0.3}s"

        for file_number in range(expected_num_files):
            curr_file = files_data[file_number]

            assert file_number * bytes_per_file == curr_file.obs_offset, (
                f"expected obs_offset for file {curr_file.name} {file_number * bytes_per_file}"
                f", actual={curr_file.obs_offset}"
            )

            if file_number < expected_num_files - 1:
                expected_data_size = bytes_per_file
            else:
                expected_data_size = total_data_size - file_number * bytes_per_file

            assert curr_file.data_size == expected_data_size, (
                f"expected data_size for file {curr_file.name} is {expected_data_size}B "
                f"but it has {curr_file.data_size}B"
            )

    def check_weights_contain_dropped_packets(
        self: DspDataAnalyser,
        expected_dropped_packets: List[int],
    ) -> None:
        """Analyse DSP weights files.

        This will parse all weights files in self.dsp_mount / self.subsystem_id / $SCAN_ID / weights
        and check that the specified packets are flagged as dropped.
        """
        file_path = (
            pathlib.Path(self.dsp_mount) / self.eb_id / self.subsystem_id / str(self.scan_id) / "weights"
        )

        dropped_packets: List[int] = []
        weights_files = file_path.glob("*.dada")
        for f in weights_files:
            self.logger.info(f"Opening weights file={f} with WeightsFileReader")
            with WeightsFileReader(f, logger=self.logger, unpack_scales=True, unpack_weights=False) as file:
                dropped_packets.extend(file.dropped_packets)

        self.logger.info(
            f"Found dropped packets {len(dropped_packets)}, searching for {expected_dropped_packets}"
        )
        assert set(expected_dropped_packets).issubset(
            set(dropped_packets)
        ), f"Expected {expected_dropped_packets} to be within recorded dropped packets"
