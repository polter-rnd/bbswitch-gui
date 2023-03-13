"""Module containing utilities for monitoring bbswitch states."""

from typing import Any, Callable, Optional, Tuple
from gi.repository import Gio, GLib  # pyright: ignore

BBSWITCH_PATH = '/proc/acpi/bbswitch'       # Path to bbswitch control file
BBSWITCHD_SOCK = '/var/run/bbswitchd.sock'  # Path to bbswitchd socket


class BBswitchClientException(Exception):
    """Exception thrown by :class:`BBswitchClient` class methods."""


class BBswitchClient():
    """Communicates with bbswitchd to change GPU state."""

    def __init__(self) -> None:
        """Initialize client for bbswitchd."""
        self._cancellable: Optional[Gio.Cancellable] = None

    def _socket_init(self) -> Gio.SocketClient:
        client = Gio.SocketClient()
        client.set_socket_type(Gio.SocketType.DATAGRAM)
        client.set_local_address(Gio.UnixSocketAddress.new_with_type(
            b'\0',
            Gio.UnixSocketAddressType.ABSTRACT
        ))
        return client

    def in_progress(self) -> bool:
        """Check if there is operating penging.

        :return: `True` if in progress, `False` otherwise
        """
        return self._cancellable is not None

    def cancel(self) -> None:
        """Cancel pending operation if any."""
        if self._cancellable:
            self._cancellable.cancel()
            self._cancellable = None

    def send_command(self, command: str) -> Optional[str]:
        """Send arbitary command to bbswitchd.

        Call is synchronous.

        :raises: :class:`BBswitchClientException` on failure
        :return: Response from server
        """
        client = self._socket_init()
        try:
            conn = client.connect(Gio.UnixSocketAddress.new(BBSWITCHD_SOCK))
            conn.get_output_stream().write_bytes(
                GLib.Bytes.new(command.encode('ascii') + b'\0'))
            gdata = conn.get_input_stream().read_bytes(1024)
            data = gdata.get_data() if gdata else None
        except GLib.GError as err:  # type: ignore
            raise BBswitchClientException(err.message) from err  # type: ignore
        return data.decode() if data else None

    def set_gpu_state(self, state: bool,
                      on_finished: Callable[[Optional[BBswitchClientException]], None]) -> None:
        """Set GPU enabled state (`True` or `False`).

        Call is asynchronous, use ``on_finished`` callback to handle result.

        :param state: `True` means GPU will be enabled, `False` - disabled.
        :param on_finished: Callback to be called after switch change finish.
                            In case of error :class:`BBswitchClientException`
                            will be passed as first positional argument, `None` otherwise.
        """
        self._cancellable = Gio.Cancellable()

        client = self._socket_init()
        client.connect_async(
            Gio.UnixSocketAddress.new(BBSWITCHD_SOCK),
            self._cancellable,
            self._on_connect_finished,
            state, on_finished)

    def _on_connect_finished(self, client, result, state, on_finished):
        try:
            conn = client.connect_finish(result)
            conn.get_output_stream().write_bytes_async(
                GLib.Bytes.new(b'on\0' if state else b'off\0'),
                GLib.PRIORITY_LOW,
                self._cancellable,
                None)
            conn.get_input_stream().read_bytes_async(
                1024,
                GLib.PRIORITY_LOW,
                self._cancellable,
                self._on_read_finished,
                on_finished)
        except GLib.GError as err:  # type: ignore
            self._cancellable = None
            on_finished(BBswitchClientException(err.message))  # type: ignore

    def _on_read_finished(self, stream, result, on_finished):
        error = None
        try:
            gdata = stream.read_bytes_finish(result)
            data = gdata.get_data() if gdata else None
            if data and data != b'\0':
                error = BBswitchClientException(data.decode())
        except GLib.GError as err:  # type: ignore
            error = BBswitchClientException(err.message)  # type: ignore

        self._cancellable = None
        on_finished(error)


class BBswitchMonitorException(Exception):
    """Exception thrown by :class:`BBswitchMonitor` class methods."""


class BBswitchMonitor:
    """Wrapper for monitoring bbswitch module status."""

    def __init__(self) -> None:
        """Initialize file monitoring for BBSWITCH_PATH."""
        self.file = Gio.File.new_for_path(BBSWITCH_PATH)
        self.monitor = self.file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.connection: Optional[int] = None
        self.callback: Optional[Callable] = None
        self.callback_args: Tuple[Any, ...] = ()

    def get_gpu_state(self) -> Tuple[str, bool]:
        """Return a tuple with PCI bus ID and it's enabled state (`True` or `False`).

        :raises: :class:`BBswitchMonitorException` on failure
        :return: Tuple with GPU id and state (e.g. `( "0000:01:00.0", True )`)
        """
        try:
            _, contents, _ = self.file.load_contents()
        except GLib.GError as err:  # type: ignore
            raise BBswitchMonitorException(err.message) from err  # type: ignore

        for line in contents.decode().splitlines():
            space = line.find(' ')
            if space == -1:
                raise BBswitchMonitorException(f'Failed to parse "{self.file.get_path()}"')

            bus_id = line[:space]
            state = line[space + 1:]
            if state not in ['ON', 'OFF']:
                raise BBswitchMonitorException(f'Unknown bbswitch state "{state}"')

            return (bus_id, state == 'ON')

        raise BBswitchMonitorException(f'Looks like "{self.file.get_path()}" is empty')

    def monitor_start(self, on_change: Callable, *on_change_args: Any) -> None:
        """Start monitoring changes of GPU states.

        Calls the callback with optional arguments on each state change.
        If monitor was already started, only callback with arguments will be updated.

        :param on_change: Callback to be called on GPU state change
        :param on_change_args: Optional arguments to on_change()
        """
        self.callback = on_change
        self.callback_args = on_change_args
        if self.connection is None:
            self.callback(*self.callback_args)
            self.connection = self.monitor.connect('changed', self._on_monitor_event_changed)

    def monitor_stop(self) -> None:
        """Stop monitoring changes of GPU states."""
        if self.connection is not None:
            self.monitor.disconnect(self.connection)
            self.connection = None
            self.callback = None
            self.callback_args = ()

    def _on_monitor_event_changed(self, monitor, file, other_file, event_type):
        del monitor, file, other_file  # unused arguments
        if event_type == Gio.FileMonitorEvent.CHANGED:
            # Do not call a callback if monitor has been stopped
            if self.callback is not None:
                self.callback(*self.callback_args)
        return True
