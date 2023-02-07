"""Module containing utilities for monitoring NVIDIA GPUs."""

from typing import Any, Callable, List, TypedDict
from gi.repository import GObject

try:
    import pynvml
except ImportError:
    from py3nvml import py3nvml as pynvml

from .psutil import PSUtil, PSUtilException

NVIDIA_DEV = '/dev/nvidia0'  # Path to NVIDIA device


class NVidiaGpuProcessInfo(TypedDict):
    """Class for storing per-process GPU information."""

    pid: int
    """Process PID"""

    mem_used: int
    """Memory usage (MiB)"""

    cmdline: str
    """Process name and arguments"""


class NVidiaGpuInfo(TypedDict):
    """Class for storing GPU information."""

    gpu_temp: int
    """Temperature (°C)"""

    power_draw: float
    """Power usage (W)"""

    mem_used: int
    """Memory usage (MiB)"""

    mem_total: int
    """Total GPU memory (MiB)"""

    gpu_util: int
    """GPU utilization (%)"""

    processes: List[NVidiaGpuProcessInfo]
    """List of processes running on GPU (see :class:`NVidiaGpuProcessInfo`)"""

    modules: List[str]
    """List of NVIDIA kernel modules loaded"""


class NvidiaMonitorException(Exception):
    """Exception thrown by :class:`NvidiaMonitor` class methods."""


class NvidiaMonitor():
    """Wrapper for executing nvidia-smi and parsing output."""

    def __init__(self, timeout: int = 1):
        """Initialize monitoring for `nvidia-smi` output.

        :param timeout: How often to check for GPU information, in seconds
        """
        self.timeout = timeout
        self.timer = None
        self.callback = None
        self.callback_args = None

    def gpu_info(self, bus_id: str) -> NVidiaGpuInfo:
        """Return NVIDIA GPU information.

        Uses `NVML` library internally.

        :param bus_id: PCI bus ID of NVIDIA GPU
        :raises: :class:`NvidiaMonitorException` on failure
        """
        res: NVidiaGpuInfo = {
            'gpu_temp': 0,
            'power_draw': 0.0,
            'mem_used': 0,
            'mem_total': 0,
            'gpu_util': 0,
            'processes': [],
            'modules': []
        }

        # Currently loaded NVIDIA kernel modules
        res['modules'] = self._get_modules()

        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()

            for i in range(0, device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                pci_info = pynvml.nvmlDeviceGetPciInfo(handle)

                if hasattr(pci_info, 'busIdLegacy') and pci_info.busIdLegacy.decode() != bus_id:
                    continue
                if pci_info.busId.decode() != bus_id:
                    continue

                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                res['mem_total'] = round(mem_info.total / 1024 / 1024)
                res['mem_used'] = round(mem_info.used / 1024 / 1024)

                util_rates = pynvml.nvmlDeviceGetUtilizationRates(handle)
                res['gpu_util'] = util_rates.gpu

                gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                res['gpu_temp'] = gpu_temp

                power_usage = pynvml.nvmlDeviceGetPowerUsage(handle)
                res['power_draw'] = power_usage / 1000.0

                # Get all pids from fuser, they may be not visible through NVML
                fuser_pids = PSUtil.get_fuser_pids(NVIDIA_DEV)
                # Get everything available from NVML, gather memory usage
                for proc in pynvml.nvmlDeviceGetComputeRunningProcesses(handle) \
                        + pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle):
                    # If process was listed by fuser, remove it, we will add more info
                    if proc.pid in fuser_pids:
                        fuser_pids.remove(proc.pid)
                    # If process was already added (like in case of C+G type)
                    if next((p for p in res['processes'] if p['pid'] == proc.pid), None):
                        continue
                    res['processes'].append({
                        'pid': proc.pid,
                        'mem_used': round(proc.usedGpuMemory / 1024 / 1024),
                        'cmdline': PSUtil.get_cmdline(proc.pid)
                    })
                # Add all fuser PIDs that were not present in NVML
                for pid in fuser_pids:
                    res['processes'].append({
                        'pid': pid,
                        'mem_used': None,
                        'cmdline': PSUtil.get_cmdline(pid)
                    })

                return res
        except (pynvml.NVMLError, PSUtilException) as err:
            if hasattr(err, 'value') and err.value == pynvml.NVML_ERROR_DRIVER_NOT_LOADED:
                # If driver is not loaded, just ignore this and return None
                return None

            raise NvidiaMonitorException(f'NVMLError: {err}') from err
        finally:
            # Don't forget to release resources
            if pynvml.nvmlLib is not None:
                pynvml.nvmlShutdown()

        raise NvidiaMonitorException(f'GPU {bus_id} not found in nvidia-smi')

    def monitor_start(self, on_change: Callable, *on_change_args: Any) -> None:
        """Start monitoring changes of nvidia-smi info.

        Calls the callback with optional arguments every several seconds.
        If monitor was already started, only callback with arguments will be updated.

        :param on_change: Callback to be called on GPU state change
        :param on_change_args: Optional arguments to on_change()
        """
        self.callback = on_change
        self.callback_args = on_change_args
        if self.timer is None:
            self.callback(*self.callback_args)
            self.timer = GObject.timeout_add_seconds(self.timeout, self._timer_callback)

    def monitor_stop(self) -> None:
        """Stop monitoring changes of GPU states."""
        if self.timer is not None:
            GObject.source_remove(self.timer)
            self.timer = None

    def _get_modules(self):
        modules = []
        try:
            with open('/proc/modules', encoding='utf-8') as file:
                for line in file:
                    parts = line.split(' ')
                    if len(parts) > 0:
                        if line.startswith('nvidia'):
                            modules.append(parts[0])
                        elif line.startswith('nouveau'):
                            raise NvidiaMonitorException(
                                'Nouveau is not supported. '
                                'Please install NVIDIA proprietary driver!'
                            )
        except OSError as err:
            raise NvidiaMonitorException(err) from err
        return modules

    def _timer_callback(self):
        # Do not call a callback if timer has been stopped
        if self.timer is not None:
            self.callback(*self.callback_args)
        return True
