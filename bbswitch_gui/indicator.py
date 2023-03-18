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
            'customtray', '',
            AppIndicator3.IndicatorCategory.HARDWARE)
        self._app_indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._app_indicator.set_menu(self._menu())
        self._enabled = False

    def reset(self) -> None:
        """Reset indicator to default state."""
        self.set_state(False)
        self._switch_item.set_sensitive(False)

    def set_state(self, enabled: bool) -> None:
        """Set power state of dedicated GPU."""
        self._enabled = enabled
        self._app_indicator.set_icon('bbswitch-tray-active-symbolic' if enabled else
                                     'bbswitch-tray-symbolic')
        self._app_indicator.set_title('Giscrete GPU: On' if enabled else
                                      'Giscrete GPU: Off')
        self._switch_item.set_label('Turn GPU Off' if enabled else
                                    'Turn GPU On')
        self._switch_item.set_image(Gtk.Image.new_from_icon_name(
            'bbswitch-on-symbolic' if enabled else
            'bbswitch-off-symbolic',
            Gtk.IconSize.MENU))  # type: ignore
        self._switch_item.set_sensitive(True)

    def _menu(self):
        menu = Gtk.Menu()

        self._switch_item = Gtk.ImageMenuItem()
        self._switch_item.set_always_show_image(True)  # type: ignore
        self._switch_item.connect('activate', self._request_power_state_switch)
        menu.append(self._switch_item)

        menu.append(Gtk.SeparatorMenuItem())

        self.open_item = Gtk.MenuItem('Open Window')
        self.open_item.connect('activate', self._request_open)
        menu.append(self.open_item)

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
