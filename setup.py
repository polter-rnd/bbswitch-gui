#!/usr/bin/env python

"""
    To install bbswitch-gui on a GNU/Linux distribution, run:
    pip3 install .
"""

from setuptools import setup

# Check if py3nvml installed
try:
    import py3nvml
    py3nvml_found=True
except ImportError:
    py3nvml_found=False


if __name__ == '__main__':
    setup(
        install_requires=[
            'PyGObject>=3.34.0',
            'py3nvml>=0.2.7' if py3nvml_found else 'pynvml>=7.352.0'
        ]
    )
