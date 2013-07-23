# Standard library modules.
import logging
import os
import re
import sys

# Initialize a logger.
logger = logging.getLogger(__name__)

class Workin:

    def __init__(self, wd):
        self.wd = wd
        self.old_wd = None

    def __enter__(self):
        if self.wd:
            self.old_wd = os.getcwd()
            os.chdir(self.wd)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_wd:
            os.chdir(self.old_wd)

def compact(text, **kw):
    """
    Trim and compact whitespace and .format() the resulting string.
    """
    return ' '.join(text.split()).format(**kw)

previously_transformed_names = {}

def transform_package_name(*words):
    """
    Transforms the name of a Python package as found on PyPi into the name that
    we want it to have as a Debian package using a prefix and a seperator.
    """
    if words not in previously_transformed_names:
        # Transform ('python', 'python-debian') into ('python', 'python', 'debian').
        normalized_words = '-'.join(w.lower() for w in words).split('-')
        logger.debug("Transforming package name, step 1: Split words (%r)", normalized_words)
        # Remove repeating words.
        deduplicated_words = list(normalized_words)
        i = 0
        while i < len(deduplicated_words):
            if i + 1 < len(deduplicated_words) and deduplicated_words[i] == deduplicated_words[i + 1]:
                deduplicated_words.pop(i)
            else:
                i += 1
        logger.debug("Transforming package name, step 2: Removed redundant words (%r)", deduplicated_words)
        # Make sure that the only non-alphanumeric character is the dash.
        name = re.sub('[^a-z0-9]+', '-', ' '.join(deduplicated_words)).strip('-')
        logger.debug("Transforming package name, step 3: Normalizing special characters (%r)", name)
        previously_transformed_names[words] = name
    return previously_transformed_names[words]

def run(command, wd=None, verbose=False):
    """
    Advanced version of :py:func:`os.system()` that can change the working
    directory and silence external commands (if the command ends with a nonzero
    exit code the output will be shown anyway).

    :param command: The shell command line to execute (a string).
    :param wd: The working directory for the command (a string, optional).
    :param verbose: ``True`` if the output of the command should be shown,
                    ``False`` if the output should be hidden (the default).
    """
    with Workin(wd):
        if verbose:
            exitcode = os.system(command + ' 1>&2')
        else:
            handle = os.popen(command + ' 2>&1')
            output = handle.read()
            exitcode = handle.close()

            if exitcode:
                sys.stderr.write(output)

    return exitcode

def is_lucid_lynx():
    """
    Check the contents of ``/etc/issue.net`` to determine whether we are
    running on Ubuntu 10.04 (Lucid Lynx).

    :returns: ``True`` if running on Ubuntu 10.04, ``False`` otherwise.
    """
    try:
        with open('/etc/issue.net') as handle:
            return '10.04' in handle.read()
    except Exception:
        return False
