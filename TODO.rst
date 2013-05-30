To-do list for the Python to Debian converter
=============================================

- Extend ``README.rst`` so that it's all that's needed to get up to speed with the project.
- Use the logging module so we can show messages on the console *and* write them to a log file.
- Make the build/package directories and the package name transformation configurable from ``control.ini``...
- Support configuration in ``/etc/paylogic/py2deb.ini`` or something similar (a system configuration).
- Add confirmation for installation of non-python dependencies *and* add a command to auto-confirm everything (--yes)
- Use sanity_check_dependencies() from pip_accel.deps
- Implement a patch configuration option to patch packages from PyPI.
- Command-line option: do not follow dependencies.
- Command-line option: Alternative config file
