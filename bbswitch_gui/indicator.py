"""Module containing tray indicator."""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import GObject, Gtk, AppIndicator3  # pyright: ignore


class Indicator(GObject.GObject):
    """Tray Indicator."""

    __gtype_name__ = "Indicator"
    __gsignals__ = {
        'open-requested': (GObject.SIGNAL_RUN_LAST,
                           GObject.TYPE_NONE, ()),
        'exit-requested': (GObject.SIGNAL_RUN_LAST,
                           GObject.TYPE_NONE, ()),
        'power-state-switch-requested': (GObject.SIGNAL_RUN_LAST,
                                         GObject.TYPE_NONE, (bool,))
    }

    def __init__(self, **kwargs) -> None:
        """Initialize Tray Indicator."""
        super().__init__(**kwargs)

        self._app_indicator = AppIndicator3.Indicator.new(
            'customtray', 'bbswitch-tray-symbolic',
            AppIndicator3.IndicatorCategory.HARDWARE)
        self._app_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._enabled = False
        self._sensitive = False

    def reset(self) -> None:
        """Reset indicator to default state."""
        self.set_state(False, False)

    def set_state(self, enabled: bool, sensitive: bool = True) -> None:
        """Set power state of dedicated GPU."""
        self._enabled = enabled
        self._sensitive = sensitive
        self._app_indicator.set_icon('bbswitch-tray-active-symbolic' if enabled else
                                     'bbswitch-tray-symbolic')
        self._app_indicator.set_title('Discrete GPU: On' if enabled else
                                      'Discrete GPU: Off')
        self._app_indicator.set_menu(self._menu())

    def _menu(self):
        menu = Gtk.Menu()

        switch_item = Gtk.ImageMenuItem()
        switch_item.set_always_show_image(True)  # type: ignore
        switch_item.connect('activate', self._request_power_state_switch)

        switch_item.set_label('Turn GPU Off' if self._enabled else
                              'Turn GPU On')
        switch_item.set_image(Gtk.Image.new_from_icon_name(
            'bbswitch-on-symbolic' if self._enabled else
            'bbswitch-off-symbolic',
            Gtk.IconSize.MENU))  # type: ignore
        switch_item.set_sensitive(self._sensitive)

        menu.append(switch_item)

        menu.append(Gtk.SeparatorMenuItem())

        open_item = Gtk.MenuItem('Open Window')
        open_item.connect('activate', self._request_open)
        menu.append(open_item)

        close_item = Gtk.MenuItem('Exit')
        close_item.connect('activate', self._request_exit)
        menu.append(close_item)

        menu.show_all()
        return menu

    def _request_open(self, menuitem):
        del menuitem  # unused argument
        self.emit('open-requested')

    def _request_exit(self, menuitem):
        del menuitem  # unused argument
        self.emit('exit-requested')

    def _request_power_state_switch(self, menuitem):
        del menuitem  # unused argument
        self.emit('power-state-switch-requested', not self._enabled)
