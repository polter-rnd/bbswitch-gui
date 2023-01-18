message('Checking dependencies')

py_mod = import('python')
python = py_mod.find_installation('python3',
    modules: [ 'gi', 'pynvml' ],
    required: false
)
if not python.found()
    # Try py3nvml instead of pynvml
    python = py_mod.find_installation('python3',
        modules: [ 'gi', 'py3nvml' ]
    )
endif

# Check GTK+ version
gtk3_check = run_command(python,
    ['-c', 'import gi; gi.require_version("Gtk", "3.0")'],
    check : false
)
assert(gtk3_check.returncode() == 0,
       'Check if GTK+3 is installed')

py_sources = [
    '__init__.py',
    'application.py',
    'bbswitch.py',
    'nvidia.py',
    'pciutil.py',
    'psutil.py',
    'view.py'
]
python.install_sources(py_sources,
    subdir : 'bbswitch_gui'
)

install_data([
    'ui/bbswitch-gui.glade',
    'ui/style.css'
], install_dir : python.get_install_dir() / 'bbswitch_gui/ui')
