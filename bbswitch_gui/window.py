"""Module containing the user interface."""

import os
import signal
import logging
from pkg_resources import resource_filename

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import GObject, Gtk, Gdk, Pango

from .nvidia import NVidiaGpuInfo

logger = logging.getLogger(__name__)


@Gtk.Template(filename=resource_filename(__name__, 'ui/bbswitch-gui.glade'))
class MainWindow(Gtk.ApplicationWindow):
    """Main application window."""

    __gtype_name__ = "MainWindow"
    __gsignals__ = {
        'power-state-switch-requested': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (bool,))
    }

    state_switch = Gtk.Template.Child()
    modules_label = Gtk.Template.Child()

    monitor_bar = Gtk.Template.Child()
    temperature_label = Gtk.Template.Child()
    power_label = Gtk.Template.Child()
    memory_label = Gtk.Template.Child()
    utilization_label = Gtk.Template.Child()

    bar_stack = Gtk.Template.Child()
    info_label = Gtk.Template.Child()
    error_label = Gtk.Template.Child()
    warning_label = Gtk.Template.Child()
    header_bar = Gtk.Template.Child()

    processes_store = Gtk.Template.Child()
    processes_view = Gtk.Template.Child()
    pid_column = Gtk.Template.Child()
    memory_column = Gtk.Template.Child()
    name_column = Gtk.Template.Child()
    check_column = Gtk.Template.Child()

    kill_button = Gtk.Template.Child()
    toggle_button = Gtk.Template.Child()

    # Disable following warnings on dynamic GObject types
    # pylint: disable=no-member

    def __init__(self, app, **kwargs):
        """Initialize GUI widgets."""
        super().__init__(**kwargs)
        self.set_application(app)

        provider = Gtk.CssProvider()
        provider.load_from_path(resource_filename(
            __name__, 'ui/style.css'))

        Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        number_renderer = Gtk.CellRendererText()
        number_renderer.set_property('xalign', 1.0)
        self.pid_column.pack_start(number_renderer, True)
        self.pid_column.add_attribute(number_renderer, 'text', 0)
        self.memory_column.pack_start(number_renderer, True)
        self.memory_column.add_attribute(number_renderer, 'text', 1)

        text_renderer = Gtk.CellRendererText()
        text_renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.name_column.pack_start(text_renderer, True)
        self.name_column.add_attribute(text_renderer, 'text', 2)

        check_renderer = Gtk.CellRendererToggle()
        self.check_column.pack_start(check_renderer, False)
        self.check_column.add_attribute(check_renderer, 'active', 3)

    def reset(self) -> None:
        """Reset window to default state."""
        self.header_bar.set_title('bbswitch-gui')
        self.header_bar.set_subtitle('')
        self.state_switch.set_state(False)
        self.state_switch.set_sensitive(False)
        self.kill_button.set_sensitive(False)
        self.toggle_button.set_sensitive(False)
        self.processes_store.clear()

    def update_header(self, bus_id: str, enabled: bool, vendor: str, device: str) -> None:
        """Update headerbar for selected GPU.

        :param bus_id: PCI bus ID
        :param enabled: is GPU enabled (`True` or `False`)
        :param vendor: PCI vendor name (or `None` if not available)
        :param device: PCI device name (or `None` if not available)
        """
        if enabled and not self.state_switch.get_state():
            self.show_info('Discrete graphics card is turned on')
        else:
            self.show_info('Discrete graphics card is turned off')

        self.state_switch.set_state(enabled)
        self.state_switch.set_sensitive(True)

        if device is None:
            self.header_bar.set_title(f'NVIDIA GPU on {bus_id}')
        else:
            self.header_bar.set_title(device[device.find('[') + 1:device.find(']')])

        if vendor is None:
            self.header_bar.set_subtitle('Additional PCI info is not available')
        else:
            self.header_bar.set_subtitle(vendor)

    def update_monitor(self, gpu_info: NVidiaGpuInfo) -> None:
        """Update UI for selected GPU.

        :param gpu_info: Dictionary of additional GPU information
        """
        self._set_bar_stack_page('monitor')

        # Helper to convert memory in megabytes to string
        def format_mem(mem: int) -> str:
            return f'{mem} MiB' if mem else 'N/A'

        # Update GPU parameters
        self.temperature_label.set_text(str(gpu_info['gpu_temp']) + ' °C')
        self.power_label.set_text(f"{gpu_info['power_draw']:.2f} W")
        self.memory_label.set_text(str(gpu_info['mem_used']) + ' / ' +
                                   format_mem(gpu_info['mem_total']))
        self.utilization_label.set_text(str(gpu_info['gpu_util']) + ' %')

        # Update existing PIDs
        processes = gpu_info['processes']
        i = self.processes_store.get_iter_first()
        while i is not None:
            i_next = self.processes_store.iter_next(i)
            pid = self.processes_store.get_value(i, 0)
            cmdline = self.processes_store.get_value(i, 2)
            process = next((p for p in processes if p['pid'] == pid), None)
            if process is not None and process['cmdline'] == cmdline:
                self.processes_store.set_value(i, 1, format_mem(process['mem_used']))
                processes.remove(process)
            else:
                self.processes_store.remove(i)
            i = i_next

        # Add new PIDs
        for process in processes:
            self.processes_store.append([
                process['pid'],
                format_mem(process['mem_used']),
                process['cmdline'],
                False
            ])

        # Update modules
        self.modules_label.set_text(
            '\n'.join(['• ' + m for m in gpu_info['modules']]))

    def show_info(self, message) -> None:
        """Show information bar with informational message.

        :param message: Error text
        """
        self.info_label.set_text(message)
        self._set_bar_stack_page('info')

    def show_warning(self, message) -> None:
        """Show information bar with warning message.

        :param message: Error text
        """
        self.warning_label.set_text(message)
        self._set_bar_stack_page('warning')

    def show_error(self, message) -> None:
        """Show information bar with error message.

        :param message: Error text
        """
        self.error_label.set_text(message)
        self._set_bar_stack_page('error')

    def error_dialog(self, title, message) -> None:
        """Raise modal message dialog with error text.

        :param message: Error text
        """
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def set_cursor_busy(self) -> None:
        """Set the mouse to be a hourglass."""
        watch = Gdk.Cursor(Gdk.CursorType.WATCH)
        gdk_window = self.get_window()
        gdk_window.set_cursor(watch)

    def set_cursor_arrow(self):
        """Set the mouse to be a normal arrow."""
        arrow = Gdk.Cursor(Gdk.CursorType.ARROW)
        gdk_window = self.get_window()
        gdk_window.set_cursor(arrow)

    def _set_bar_stack_page(self, name: str):
        page = self.bar_stack.get_child_by_name(name)
        if page:
            self.bar_stack.set_visible_child(page)

    def _get_selected_pids(self):
        pids = []
        self.processes_store.foreach(
            lambda store, path, iter, data:
                data.append(store[path][0]) if store[path][3] else None,
            pids)
        return pids

    @Gtk.Template.Callback()
    def _on_process_activated(self, treeview, path, column):
        del treeview, column  # unused argument
        # pylint: disable=unsubscriptable-object
        self.processes_store[path][3] = not self.processes_store[path][3]
        self.kill_button.set_sensitive(len(self._get_selected_pids()) > 0)

    @Gtk.Template.Callback()
    def _on_process_added_or_removed(self, store, path=None, iterator=None):
        del store, path, iterator  # unused argument
        self.kill_button.set_sensitive(len(self._get_selected_pids()) > 0)
        self.toggle_button.set_sensitive(self.processes_store.iter_n_children() > 0)

    @Gtk.Template.Callback()
    def _on_kill_button_clicked(self, button):
        del button  # unused argument
        for pid in self._get_selected_pids():
            print(pid)
            os.kill(pid, signal.SIGKILL)

    @Gtk.Template.Callback()
    def _on_toggle_button_clicked(self, button):
        del button  # unused argument
        row_count = self.processes_store.iter_n_children()
        if row_count == 0:
            # Nothing to select/deselect
            return
        elif row_count != len(self._get_selected_pids()):
            # Select all
            self.processes_store.foreach(
                lambda store, path, iter: store.set_value(iter, 3, True))
            self.kill_button.set_sensitive(True)
        else:
            # Deselect all
            self.processes_store.foreach(
                lambda store, path, iter: store.set_value(iter, 3, False))
            self.kill_button.set_sensitive(False)

    @Gtk.Template.Callback()
    def _on_switch_pressed(self, switch, gdata):
        del gdata  # unused argument
        self.emit('power-state-switch-requested', not switch.get_active())
        return True
