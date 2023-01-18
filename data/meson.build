prefix = get_option('prefix')
datadir = prefix / get_option('datadir')
icondir = datadir / 'icons/hicolor/scalable'

install_data([
    'icons/bbswitch-gpu-symbolic.svg',
    'icons/bbswitch-power-symbolic.svg',
    'icons/bbswitch-ram-symbolic.svg',
    'icons/bbswitch-temp-symbolic.svg'
], install_dir : icondir / 'status')

install_data('icons/bbswitch-gui.svg',
    install_dir : icondir / 'apps')

desktop_file_conf = configuration_data()
desktop_file_conf.set('BINDIR', get_option('prefix') / get_option('bindir'))

configure_file(
    configuration : desktop_file_conf,
    input : 'bbswitch-gui.desktop.in',
    output : 'bbswitch-gui.desktop',
    install : true,
    install_dir : datadir / 'applications'
)
