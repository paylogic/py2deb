# Standard library modules.
import logging
import os
import re
import sys
import time

# External dependencies.
from deb_pkg_tools.control import merge_control_fields
from executor import execute

# Modules included in our package.
from py2deb.config import config
from py2deb.exceptions import BackendFailed

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

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
            if name not in ('debian-name', 'script'):
                overrides[name] = value
    if overrides:
        control_fields = merge_control_fields(control_fields, overrides)
    return control_fields

def transform_package_name(name_prefix, python_package_name, is_isolated_package=False):
    """
    Transforms the name of a Python package as found on PyPi into the name that
    we want it to have as a Debian package using a prefix and a seperator.
    """
    if not is_isolated_package and config.has_option(python_package_name, 'debian-name'):
        debian_package = config.get(python_package_name, 'debian-name')
        logger.debug("Package %s has overridden Debian package name configured: %s", python_package_name, debian_package)
    else:
        # Apply the package name prefix.
        debian_package = '%s-%s' % (name_prefix, python_package_name)
        normalized_words = debian_package.lower().split('-')
        # Remove repeating words.
        deduplicated_words = list(normalized_words)
        i = 0
        while i < len(deduplicated_words):
            if i + 1 < len(deduplicated_words) and deduplicated_words[i] == deduplicated_words[i + 1]:
                deduplicated_words.pop(i)
            else:
                i += 1
        # Make sure that the only non-alphanumeric character is the dash.
        debian_package = re.sub('[^a-z0-9]+', '-', ' '.join(deduplicated_words)).strip('-')
        logger.debug("Package %s has normalized Debian package name %s", python_package_name, debian_package)
    return debian_package

def apply_script(config, package_name, directory):
    """
    Checks if a line of shell script is defined in the configuration and
    executes it with the directory of the package as the current working
    directory.
    """
    if config.has_option(package_name, 'script'):
        command = config.get(package_name, 'script')
        logger.debug("%s: Executing shell command %s in %s ..",
                     package_name, command, directory)
        if not execute(command, directory=directory, check=False):
            msg = "Failed to apply script to %s!"
            raise BackendFailed, msg % package_name
        logger.debug("%s: Shell command has been executed.", package_name)

def get_tagged_description():
  """
  Get a package description tagged with the name `py2deb` and the current
  date/time.
  """
  return compact(time.strftime('Packaged by py2deb on %B %e, %Y at %H:%M'))

def find_ubuntu_release():
    """
    Find the code name of the Ubuntu release we're running.

    :returns: The name of the release, a string like ``lucid`` or ``precise``.
    """
    lsb_release = os.popen('lsb_release --short --codename 2>/dev/null')
    distribution = lsb_release.read().strip()
    logger.debug("Detected Ubuntu release: %s", distribution.capitalize())
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

def check_supported_platform():
    """
    Determine whether the old (0.6.0) or new (0.6.0+git) release of ``stdeb``
    should be used to convert Python packages to Debian packages.
    """
    # First let's make sure we're running some form of Debian Linux.
    if not os.path.isfile('/etc/debian_version'):
        raise Exception, compact("""
            To run py2deb (and stdeb) you need to be running Debian Linux or a
            derived Linux distribution like Ubuntu!
        """)
    # Now determine whether we are running either one of the Ubuntu Linux
    # distribution releases Lucid Lynx (10.04 LTS) or Precise Pangolin (12.04
    # LTS). These are the only Debian Linux derived distribution releases on
    # which py2deb is currently tested and supported.
    ubuntu_release = find_ubuntu_release()
    python_version = find_python_version()
    if ubuntu_release == 'lucid' and python_version != 'python2.6':
        msg = "On Ubuntu 10.04 you should use Python 2.6 to run py2deb! (you are using %s)"
        raise Exception, msg % python_version
    elif ubuntu_release == 'precise' and python_version != 'python2.7':
        msg = "On Ubuntu 12.04 you should use Python 2.7 to run py2deb! (you are using %s)"
        raise Exception, msg % python_version
    elif ubuntu_release not in ('lucid', 'precise'):
        logger.warn(compact("""
            py2deb was developed for and tested on Ubuntu 10.04 (Python 2.6)
            and Ubuntu 12.04 (Python 2.7). Since we appear to be running on
            another platform you may experience breakage!
        """))
