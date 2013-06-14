To-do list for the Python to Debian converter
=============================================

- Accept pip command line options.
- Replace recall with a command line option to print a debian dependency line.
- Command-line option: Alternative config file.
- Make the build/package directories and the package name transformation configurable from ``control.ini``...
- Use coloredlogs so we can show messages on the console *and* write them to a log file.
- Generate a dependency tree in order to drop/replace certain dependencies with ubuntu packages.
- Add confirmation for installation of non-python dependencies *and* add a command to auto-confirm everything (--yes)
- Implement a patch configuration option to patch packages from PyPI using a shell script.

  * Remove fabric-paramiko patch.

- Use sanity_check_dependencies() from pip_accel.deps.
- ? Make custom exceptions