# Standard library modules.
import logging
import os
import re
import sys

# External dependencies.
from deb_pkg_tools.control import merge_control_fields

# Modules included in our package.
from py2deb.config import config

# Initialize a logger for this module.
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

def patch_control_file(package, control_fields):
    """
    Get a dictionary with control file fields for which overrides are present
    in the configuration file bundled with py2deb or provided by the user.
    """
    overrides = {}
    if config.has_section(package.name):
        for name, value in config.items(package.name):
            if name != 'script':
                overrides[name] = value
    return merge_control_fields(control_fields, overrides)

previously_transformed_names = {}

def transform_package_name(python_package):
    """
    Transforms the name of a Python package as found on PyPi into the name that
    we want it to have as a Debian package using a prefix and a seperator.
    """
    if python_package not in previously_transformed_names:
        if config.has_option(python_package, 'debian-name'):
            debian_package = config.get(python_package, 'debian-name')
            logger.debug("Package %s has overridden Debian package name configured: %s", python_package, debian_package)
        else:
            # Apply the package name prefix.
            debian_package = '%s-%s' % (config.get('general', 'name-prefix'), python_package)
            normalized_words = debian_package.lower().split('-')
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
            debian_package = re.sub('[^a-z0-9]+', '-', ' '.join(deduplicated_words)).strip('-')
            logger.debug("Transforming package name, step 3: Normalizing special characters (%r)", debian_package)
        previously_transformed_names[python_package] = debian_package
    return previously_transformed_names[python_package]

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
    logger.debug("Executing external command: %s", command)
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

def find_ubuntu_release():
    """
    Find the code name of the Ubuntu release we're running.

    :returns: The name of the release, a string like ``lucid`` or ``precise``.
    """
    lsb_release = os.popen('lsb_release --short --codename 2>/dev/null')
    distribution = lsb_release.read().strip()
    logger.debug("Detected Ubuntu release: %s", distribution[0].upper() + distribution[1:])
    return distribution

def find_python_version():
    """
    Find the version of Python we're running. This specifically returns a name
    matching the format of the names of the Debian packages providing the
    various available Python versions.

    :returns: A string like ``python2.6`` or ``python2.7``.
    """
    python_version = 'python%d.%d' % (sys.version_info[0], sys.version_info[1])
    logger.debug("Detected Python version: %s", python_version)
    return python_version

applicable_stdeb_release = None

def pick_stdeb_release():
    """
    Determine whether the old (0.6.0) or new (0.6.0+git) release of ``stdeb``
    should be used to convert Python packages to Debian packages.
    """
    global applicable_stdeb_release
    if not applicable_stdeb_release:
        ubuntu_release = find_ubuntu_release()
        python_version = find_python_version()
        # XXX Before we decide on an answer, make sure the answer will be valid!
        if ubuntu_release == 'lucid' and python_version != 'python2.6':
            raise Exception, "On Ubuntu 10.04 you should use Python 2.6 to run py2deb! (you are using %s)" % python_version
        elif ubuntu_release == 'precise' and python_version != 'python2.7':
            raise Exception, "On Ubuntu 12.04 you should use Python 2.7 to run py2deb! (you are using %s)" % python_version
        elif ubuntu_release not in ('lucid', 'precise'):
            logger.warn("py2deb was developed for and tested on Ubuntu 10.04 (Python 2.6)"
                        " and Ubuntu 12.04 (Python 2.7). Since we appear to be running on"
                        " another platform you may experience breakage!")
        if ubuntu_release == 'lucid':
            applicable_stdeb_release = 'old'
        else:
            applicable_stdeb_release = 'new'
    return applicable_stdeb_release
