"""Module containing main business logic."""

import time
import logging
import signal

from typing import Optional

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk  # pyright: ignore

from .pciutil import PCIUtil, PCIUtilException
from .bbswitch import BBswitchClient, BBswitchClientException
from .bbswitch import BBswitchMonitor, BBswitchMonitorException
from .nvidia import NVidiaGpuInfo, NvidiaMonitor, NvidiaMonitorException
from .window import MainWindow
from .indicator import Indicator

# Setup logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s \033[1m%(levelname)s\033[0m %(message)s')
logger = logging.getLogger(__name__)

REFRESH_TIMEOUT = 1      # How often to refresh nvidia monitor data, in seconds
MODULE_LOAD_TIMEOUT = 5  # How long to wait until nvidia module become accessible, in seconds


class Application(Gtk.Application):
    """Main application class allowing only one running instance."""

    bbswitch = BBswitchMonitor()
    client = BBswitchClient()
    nvidia = NvidiaMonitor(timeout=REFRESH_TIMEOUT)

    def __init__(self, *args, **kwargs) -> None:
        """Initialize application instance, setup command line handler."""
        super().__init__(
            *args,
            application_id='io.github.polter-rnd.bbswitch-gui',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )  # type: ignore

        self.add_main_option(
            'verbose',
            ord('v'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            'Enable debug logging',
            None,
        )
        self.add_main_option(
            'minimize',
            ord('m'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            'Minimize to system tray',
            None,
        )

        self._enabled_gpu: Optional[str] = None
        self._bg_notification_shown = False

        self.gpu_info: Optional[NVidiaGpuInfo] = None
        self.window: Optional[MainWindow] = None
        self.indicator: Optional[Indicator] = None

    def update_bbswitch(self) -> None:
        """Update GPU state from `bbswitch` module."""
        logging.debug('Got update from bbswitch')

        if self.indicator:
            self.indicator.reset()

        if self.window:
            self.window.reset()

        self._enabled_gpu = None
        bus_id, enabled, device, vendor = '', False, '', ''
        try:
            bus_id, enabled = self.bbswitch.get_gpu_state()
            vendor, device = PCIUtil.get_device_info(PCIUtil.get_vendor_id(bus_id),
                                                     PCIUtil.get_device_id(bus_id))
        except BBswitchMonitorException as err:
            message = str(err)
            logger.error(message)
            self.nvidia.monitor_stop()
            if self.window:
                self.window.show_error(message)
            if not self.window or not self.window.is_active():
                self._notify_error('BBswitch monitor error', message)
            return
        except PCIUtilException as err:
            logger.warning(err)

        if self.indicator:
            self.indicator.set_state(enabled)

        if self.window:
            self.window.update_header(bus_id, enabled, vendor, device)

        if enabled:
            logger.debug('Adapter %s is ON', bus_id)
            self._enabled_gpu = bus_id
            if self.window and self.window.is_visible():
                self.nvidia.monitor_start(self.update_nvidia, bus_id, time.monotonic())
        else:
            logger.debug('Adapter %s is OFF', bus_id)
            self.nvidia.monitor_stop()

    def update_nvidia(self, bus_id: str, enabled_ts: float) -> None:
        """Update GPU info from `nvidia` module.

        :param bus_id: PCI bus ID of NVIDIA GPU
        """
        logging.debug('Got update from nvidia-smi')

        try:
            self.gpu_info = self.nvidia.gpu_info(bus_id)
            if self.window:
                if self.gpu_info is None:
                    # None return value means no kernel modules available
                    if time.monotonic() - enabled_ts > MODULE_LOAD_TIMEOUT:
                        # If it took really long time, display warning
                        self.window.show_warning(
                            'NVIDIA kernel modules are not loaded. '
                            'Is the driver installed?')
                    else:
                        # Otherwise it's normal, loading modules can take some time
                        self.window.show_info('Loading NVIDIA kernel modules...')
                else:
                    self.window.update_monitor(self.gpu_info)
        except NvidiaMonitorException as err:
            message = str(err)
            logger.error(message)
            if self.window:
                self.window.show_error(message)
            if not self.window or not self.window.is_active():
                self._notify_error('NVIDIA monitor error', message)

    def do_startup(self, *args, **kwargs) -> None:
        """Handle application startup."""
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('activate', None)
        action.connect('activate', self._on_activate)  # type: ignore
        self.add_action(action)  # type: ignore

        action = Gio.SimpleAction.new('exit', None)
        action.connect('activate', self._on_quit)  # type: ignore
        self.add_action(action)  # type: ignore

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._on_quit)

    def do_activate(self, *args, **kwargs) -> None:
        """Initialize GUI.

        We only allow a single window and raise any existing ones
        """
        if not self.window:
            self.window = MainWindow(self)
            self.window.connect('power-state-switch-requested', self._on_state_switch)
            self.window.connect('delete-event', self._on_window_close)
            self.window.connect('show', self._on_window_show)
            self.window.connect('hide', self._on_window_hide)

            # Ping server so it will load bbswitch module
            try:
                self.client.send_command('status')
            except BBswitchClientException as err:
                message = str(err)
                logging.error(message)
                self.window.error_dialog(
                    'BBswitch client error',
                    message + '\n\n'
                    + 'If this happened right after installation, check the following:\n'
                    + ' • Service "bbswitchd" is enabled and running\n'
                    + ' • Active user is in effective group "bbswitchd"\n'
                    + ' • You have rebooted or restarted loginctl session')
        else:
            self.window.set_keep_above(True)
            self.window.deiconify()
            self.window.present_with_time(int(time.time()))
            self.window.set_keep_above(False)

        if not self.indicator:
            self.indicator = Indicator()
            self.indicator.connect('open-requested', self._on_activate)
            self.indicator.connect('exit-requested', self._on_quit)
            self.indicator.connect('power-state-switch-requested', self._on_state_switch)

    def do_command_line(self, *args: Gio.ApplicationCommandLine, **kwargs) -> int:
        """Handle command line arguments.

        :param args: Array of command line arguments
        :return: Exit status to fill after processing the command line
        """
        (command_line,) = args

        # convert GVariantDict -> GVariant -> dict
        options = command_line.get_options_dict().end().unpack()

        if 'verbose' in options:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug('Verbose output enabled')

        # Is GUI initialized
        initialized = self.window is not None

        self.activate()

        if self.window:
            # Utility function for starting bbswitch monitor
            def bbswitch_monitor_start(window=None, is_active=None):
                if window:
                    window.disconnect(connection)
                    if not is_active or not window.get_property(is_active.name):
                        return
                self.bbswitch.monitor_start(self.update_bbswitch)

            if 'minimize' in options:
                if not initialized:
                    # Start bbswitch monitor right now
                    bbswitch_monitor_start()
                self._bg_notification_shown = True
                self.window.hide()
            else:
                if not initialized:
                    # Start bbswitch monitor after window was activated
                    connection = self.window.connect('notify::is-active', bbswitch_monitor_start)
                self.window.show()

        return 0

    def _on_activate(self, widget=None, data=None):
        del widget, data  # unused arguments
        if self.window:
            self.activate()
        return GLib.SOURCE_CONTINUE

    def _on_quit(self, widget=None, data=None):
        del widget, data  # unused arguments
        self.withdraw_notification('error')
        self.withdraw_notification('running_in_bg')
        self.quit()
        return GLib.SOURCE_REMOVE

    def _on_state_switch_finish(self, error):
        self.withdraw_notification('error')
        if error is not None:
            logger.error(str(error))
            self.update_bbswitch()
            self._notify_error('Failed to switch power state', str(error))
        if self.window:
            self.window.set_cursor_arrow()

    def _on_state_switch(self, widget, state):
        del widget  # unused argument
        if self.client.in_progress():
            self.client.cancel()
            return

        if not state and self._enabled_gpu:
            # Update GPU info
            self.gpu_info = self.nvidia.gpu_info(self._enabled_gpu)
            if self.gpu_info and len(self.gpu_info['processes']) > 0:
                self._notify_error('NVIDIA GPU is in use',
                                   'Please stop processes using it first')
                return

        # Switch to opposite state
        self.client.set_gpu_state(state, self._on_state_switch_finish)
        if self.window:
            self.window.set_cursor_busy()

    def _notify_error(self, title, message):
        if self.window and self.window.is_active():
            self.window.error_dialog(title, message)
        else:
            notification = Gio.Notification()
            notification.set_title(title)
            notification.set_body(message)
            notification.set_default_action('app.activate')
            notification.add_button('Open Window', 'app.activate')
            self.send_notification('error', notification)

    def _on_window_show(self, window):
        del window  # unused argument
        self.withdraw_notification('running_in_bg')
        if self._enabled_gpu:
            self.nvidia.monitor_start(self.update_nvidia,
                                      self._enabled_gpu,
                                      time.monotonic())

    def _on_window_hide(self, window):
        del window  # unused argument
        self.nvidia.monitor_stop()

    def _on_window_close(self, window, event):
        del event  # unused argument
        if not self._bg_notification_shown:
            notification = Gio.Notification()
            notification.set_title('BBswitch GUI stays in background')
            notification.set_body('Could be accessed through system tray')
            notification.set_default_action('app.activate')
            notification.add_button('Open Window', 'app.activate')
            notification.add_button('Exit', 'app.exit')
            self.send_notification('running_in_bg', notification)
            self._bg_notification_shown = True
        return window.hide_on_delete()
