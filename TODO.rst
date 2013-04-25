To-do list for the Python to Debian converter
=============================================

- Extend ``README.rst`` so that it's all that's needed to get up to speed with the project.
- Implement a Graphviz dependency graph unit thingy.
- Implement a command line interface so that e.g. ``-h``, ``--help`` works properly.
- Use the logging module so we can show messages on the console *and* write them to a log file.
- Use ``pip-accel`` from PyPi using imported functions; less of a hack (the hack is then hidden inside ``pip-accel`` :-).
- Make the build/package directories and the package name transformation configurable from ``control.ini``...
- Support configuration in ``/etc/paylogic/py2deb.ini`` or something similar (a system configuration).
- An option to print a list of all the packages with versions, supported by the Depends field of a control file
