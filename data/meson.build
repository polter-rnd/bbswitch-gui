prefix = get_option('prefix')
datadir = prefix / get_option('datadir')
icondir = datadir / 'icons/hicolor/scalable'

install_data([
    'icons/bbswitch-gpu-symbolic.svg',
    'icons/bbswitch-power-symbolic.svg',
    'icons/bbswitch-ram-symbolic.svg',
    'icons/bbswitch-temp-symbolic.svg',
    'icons/bbswitch-tray-symbolic.svg',
    'icons/bbswitch-tray-active-symbolic.svg',
    'icons/bbswitch-off-symbolic.svg',
    'icons/bbswitch-on-symbolic.svg'
], install_dir : icondir / 'status')

install_data('icons/bbswitch-gui.svg',
    install_dir : icondir / 'apps')

desktop_file_conf = configuration_data()
desktop_file_conf.set('BINDIR', get_option('prefix') / get_option('bindir'))

configure_file(
    configuration : desktop_file_conf,
    input : 'io.github.polter-rnd.bbswitch-gui.desktop.in',
    output : 'io.github.polter-rnd.bbswitch-gui.desktop',
    install : true,
    install_dir : datadir / 'applications'
)
