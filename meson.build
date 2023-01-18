project('bbswitch-gui',
    version : run_command(find_program('python3'),
        ['-c', 'from bbswitch_gui import __version__; print(__version__)'],
        check : true
    ).stdout().strip()
)

# Required parts
subdir('bbswitch_gui')
subdir('data')

# Script for running application
install_data('bbswitch-gui',
             install_mode : 'rwxr-xr-x',
             install_dir : get_option('prefix') / get_option('bindir'))
