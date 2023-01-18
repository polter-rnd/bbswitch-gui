project('bbswitch-gui',
    version : '0.1.0'
)

# Required parts
subdir('bbswitch_gui')
subdir('data')

# Script for running application
install_data('bbswitch-gui',
             install_mode : 'rwxr-xr-x',
             install_dir : get_option('prefix') / get_option('bindir'))
