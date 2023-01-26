"""Module containing main business logic."""

import time
import logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk

from .pciutil import PCIUtil, PCIUtilException
from .bbswitch import BBswitchClient, BBswitchClientException
from .bbswitch import BBswitchMonitor, BBswitchMonitorException
from .nvidia import NvidiaMonitor, NvidiaMonitorException
from .window import MainWindow

# Setup logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s \033[1m%(levelname)s\033[0m %(message)s')
logger = logging.getLogger(__name__)

REFRESH_TIMEOUT = 1       # How often to refresh data, in seconds
MODULE_LOAD_TIMEOUT = 10  # Maximum time until warning will show, in seconds


class Application(Gtk.Application):
    """Main application class allowing only one running instance."""

    def __init__(self, *args, **kwargs):
        """Initialize application instance, setup command line handler."""
        super().__init__(
            *args,
            application_id='io.github.polter-rnd.bbswitch-gui',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )

        self.add_main_option(
            'verbose',
            ord('v'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            'Enable debug logging',
            None,
        )

        self.window = None
        self.bbswitch = BBswitchMonitor()
        self.client = BBswitchClient()
        self.nvidia = NvidiaMonitor(timeout=REFRESH_TIMEOUT)

        # Timestamp of last state switching
        self._state_switched_ts = 0

        # Ping server so it will load bbswitch module
        try:
            self.client.send_command('status')
        except BBswitchClientException as err:
            logging.warning(err)

    def update_bbswitch(self) -> None:
        """Update GPU state from `bbswitch` module."""
        logging.debug('Got update from bbswitch')
        self.window.reset()

        device, vendor = None, None
        try:
            bus_id, enabled = self.bbswitch.get_gpu_state()
            vendor, device = PCIUtil.get_device_info(PCIUtil.get_vendor_id(bus_id),
                                                     PCIUtil.get_device_id(bus_id))
        except BBswitchMonitorException as err:
            logger.error(err)
            self.nvidia.monitor_stop()
            if self.window:
                self.window.show_error(str(err))
            return
        except PCIUtilException as err:
            logger.warning(err)

        if self.window:
            self.window.update_header(bus_id, enabled, vendor, device)

        if enabled:
            logger.debug('Adapter %s is ON', bus_id)
            self.nvidia.monitor_start(self.update_nvidia, bus_id)
        else:
            logger.debug('Adapter %s is OFF', bus_id)
            self.nvidia.monitor_stop()

    def update_nvidia(self, bus_id) -> None:
        """Update GPU info from `nvidia` module.

        :param bus_id: PCI bus ID of NVIDIA GPU
        """
        logging.debug('Got update from nvidia-smi')

        try:
            info = self.nvidia.gpu_info(bus_id)
            if self.window:
                if info is None:
                    # None return value means no kernel modules available
                    if time.monotonic() - self._state_switched_ts > MODULE_LOAD_TIMEOUT:
                        # If it took really long time, display warning
                        self.window.show_warning(
                            'NVIDIA kernel modules not loaded. Retrying...')
                    else:
                        # Otherwise it's normal, loading modules can take some time
                        self.window.show_info('Loading NVIDIA kernel modules...')
                else:
                    self.window.update_monitor(info)
        except NvidiaMonitorException as err:
            message = str(err)
            logger.error(message)
            if self.window:
                self.window.show_error(message)

    def do_startup(self, *args, **kwargs) -> None:
        """Handle application startup."""
        Gtk.Application.do_startup(self)

    def do_activate(self, *args, **kwargs) -> None:
        """Initialize GUI.

        We only allow a single window and raise any existing ones
        """
        if not self.window:
            self.window = MainWindow(self)
            self.window.connect('power-state-switch-requested', self._on_state_switch)
            self.bbswitch.monitor_start(self.update_bbswitch)

        self.window.present()

    def do_command_line(self, *args: Gio.ApplicationCommandLine, **kwargs) -> int:
        """Handle command line arguments.

        :param args: Array of command line arguments
        :return: Exit status to fill after processing the command line
        """
        (command_line,) = args
        options = command_line.get_options_dict()
        # convert GVariantDict -> GVariant -> dict
        options = options.end().unpack()

        if 'verbose' in options:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug('Verbose output enabled')

        self.activate()
        return 0

    def _on_state_switch_finish(self, error: BBswitchClientException = None):
        if error is not None:
            logger.error(error)
            self.update_bbswitch()
            self.window.error_dialog('Failed to switch power state', str(error))
        else:
            # Save timestamp when power state has switched
            self._state_switched_ts = time.monotonic()
        self.window.set_cursor_arrow()

    def _on_state_switch(self, window, state):
        if self.client.in_progress():
            self.client.cancel()
            return

        # Switch to opposite state
        self.client.set_gpu_state(state, self._on_state_switch_finish)
        window.set_cursor_busy()
