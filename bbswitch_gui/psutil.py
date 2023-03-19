"""Module containing utilities for process management."""

import os
import subprocess  # nosec
from typing import List


class PSUtilException(Exception):
    """Exception thrown by :class:`PCIUtil` class methods."""


class PSUtil:
    """Wrapper for retrieving information about running processes."""

    @staticmethod
    def get_cmdline(pid: int) -> str:
        """Retrieve command line for running process.

        Uses `/proc/{pid}/cmdline` internally.

        :param pid: Process PID
        :return: Process name with arguments
        :raises: :class:`PSUtilException` on failure
        """
        try:
            with open(f'/proc/{pid}/cmdline', 'rb') as file:
                return file.read().replace(b'\x00', b' ').decode().rstrip()
        except OSError as err:
            raise PSUtilException(err) from err

    @staticmethod
    def get_fuser_pids(fname: str) -> List[int]:
        """Retrieve PIDs using certain file or device.

        Uses `fuser` utility internally.

        :param fname: Path to file or device
        :return: List with PIDs
        :raises: :class:`PSUtilException` on failure
        """
        try:
            proc = subprocess.run(['fuser', fname],  # nosec
                                  capture_output=True,
                                  check=True)
        except subprocess.CalledProcessError as err:
            raise PSUtilException(err) from err

        my_pid = str(os.getpid())  # Filter out our PID
        pids = [int(pid) for pid in proc.stdout.decode().split() if pid != my_pid]
        return pids
