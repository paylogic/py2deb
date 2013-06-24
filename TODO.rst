To-do list for the Python to Debian converter
=============================================

- Use ``logging.RotatingFileHandler`` to write logs to a file.
- Add confirmation for installation of non-python dependencies *and* add a command to auto-confirm everything (--yes)
- Use sanity_check_dependencies() from pip_accel.deps.

Ideas
-----
- Make custom exception(s)
- Support "extra" requirements (optional dependencies, like suggests/enhances)
- Command-line option: Create config template in current directory.