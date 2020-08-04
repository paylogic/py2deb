# Utility functions for py2deb.
#
# Authors:
#  - Arjan Verwer
#  - Peter Odding <peter.odding@paylogic.com>
# Last Change: August 4, 2020
# URL: https://py2deb.readthedocs.io

"""The :mod:`py2deb.utils` module contains miscellaneous code."""

# Standard library modules.
import logging
import os
import platform
import re
import shlex
import shutil
import sys
import tempfile

# External dependencies.
from property_manager import PropertyManager, cached_property, required_property
from deb_pkg_tools.package import find_package_archives
from six import BytesIO

# Initialize a logger.
logger = logging.getLogger(__name__)

integer_pattern = re.compile('([0-9]+)')
"""Compiled regular expression to match a consecutive run of digits."""

PYTHON_EXECUTABLE_PATTERN = re.compile(r'^(pypy|python)(\d(\.\d)?)?m?$')
"""
A compiled regular expression to match Python interpreter executable names.

The following are examples of program names that match this pattern:

- pypy
- pypy2.7
- pypy3
- python
- python2
- python2.7
- python3m
"""


class PackageRepository(PropertyManager):

    """
    Very simply abstraction for a directory containing ``*.deb`` archives.

    Used by :class:`py2deb.converter.PackageConverter` to recognize which
    Python packages have previously been converted (and so can be skipped).
    """

    def __init__(self, directory):
        """
        Initialize a :class:`PackageRepository` object.

        :param directory: The pathname of a directory containing ``*.deb`` archives (a string).
        """
        super(PackageRepository, self).__init__(directory=directory)

    @cached_property
    def archives(self):
        """
        A sorted list of package archives in :attr:`directory`.

        The value of :attr:`archives` is computed using
        :func:`deb_pkg_tools.package.find_package_archives()`.

        An example:

        >>> from py2deb import PackageRepository
        >>> repo = PackageRepository('/tmp')
        >>> repo.archives
        [PackageFile(name='py2deb', version='0.1', architecture='all',
                     filename='/tmp/py2deb_0.1_all.deb'),
         PackageFile(name='py2deb-cached-property', version='0.1.5', architecture='all',
                     filename='/tmp/py2deb-cached-property_0.1.5_all.deb'),
         PackageFile(name='py2deb-chardet', version='2.2.1', architecture='all',
                     filename='/tmp/py2deb-chardet_2.2.1_all.deb'),
         PackageFile(name='py2deb-coloredlogs', version='0.5', architecture='all',
                     filename='/tmp/py2deb-coloredlogs_0.5_all.deb'),
         PackageFile(name='py2deb-deb-pkg-tools', version='1.20.4', architecture='all',
                     filename='/tmp/py2deb-deb-pkg-tools_1.20.4_all.deb'),
         PackageFile(name='py2deb-docutils', version='0.11', architecture='all',
                     filename='/tmp/py2deb-docutils_0.11_all.deb'),
         PackageFile(name='py2deb-executor', version='1.2', architecture='all',
                     filename='/tmp/py2deb-executor_1.2_all.deb'),
         PackageFile(name='py2deb-html2text', version='2014.4.5', architecture='all',
                     filename='/tmp/py2deb-html2text_2014.4.5_all.deb'),
         PackageFile(name='py2deb-humanfriendly', version='1.8.2', architecture='all',
                     filename='/tmp/py2deb-humanfriendly_1.8.2_all.deb'),
         PackageFile(name='py2deb-pkginfo', version='1.1', architecture='all',
                     filename='/tmp/py2deb-pkginfo_1.1_all.deb'),
         PackageFile(name='py2deb-python-debian', version='0.1.21-nmu2', architecture='all',
                     filename='/tmp/py2deb-python-debian_0.1.21-nmu2_all.deb'),
         PackageFile(name='py2deb-six', version='1.6.1', architecture='all',
                     filename='/tmp/py2deb-six_1.6.1_all.deb')]

        """
        return find_package_archives(self.directory)

    @required_property
    def directory(self):
        """The pathname of a directory containing ``*.deb`` archives (a string)."""

    def get_package(self, package, version, architecture):
        """
        Find a package in the repository.

        Here's an example:

        >>> from py2deb import PackageRepository
        >>> repo = PackageRepository('/tmp')
        >>> repo.get_package('py2deb', '0.1', 'all')
        PackageFile(name='py2deb', version='0.1', architecture='all', filename='/tmp/py2deb_0.1_all.deb')

        :param package: The name of the package (a string).
        :param version: The version of the package (a string).
        :param architecture: The architecture of the package (a string).
        :returns: A :class:`deb_pkg_tools.package.PackageFile` object
                  or ``None``.
        """
        for archive in self.archives:
            if archive.name == package and archive.version == version and archive.architecture == architecture:
                return archive


class TemporaryDirectory(object):

    """
    Easy temporary directory creation & cleanup using the :keyword:`with` statement.

    Here's an example of how to use this:

    .. code-block:: python

       with TemporaryDirectory() as directory:
           # Do something useful here.
           assert os.path.isdir(directory)
    """

    def __init__(self, **options):
        """
        Initialize context manager that manages creation & cleanup of temporary directory.

        :param options: Any keyword arguments are passed on to
                        :func:`tempfile.mkdtemp()`.
        """
        self.options = options

    def __enter__(self):
        """Create the temporary directory."""
        self.temporary_directory = tempfile.mkdtemp(**self.options)
        logger.debug("Created temporary directory: %s", self.temporary_directory)
        return self.temporary_directory

    def __exit__(self, exc_type, exc_value, traceback):
        """Destroy the temporary directory."""
        logger.debug("Cleaning up temporary directory: %s", self.temporary_directory)
        shutil.rmtree(self.temporary_directory)
        del self.temporary_directory


def compact_repeating_words(words):
    """
    Remove adjacent repeating words.

    :param words: An iterable of words (strings), assumed to already be
                  normalized (lowercased).
    :returns: An iterable of words with adjacent repeating words replaced by a
              single word.

    This is used to avoid awkward word repetitions in the package name
    conversion algorithm. Here's an example of what I mean:

    >>> from py2deb import compact_repeating_words
    >>> name_prefix = 'python'
    >>> package_name = 'python-mcrypt'
    >>> combined_words = [name_prefix] + package_name.split('-')
    >>> print(list(combined_words))
    ['python', 'python', 'mcrypt']
    >>> compacted_words = compact_repeating_words(combined_words)
    >>> print(list(compacted_words))
    ['python', 'mcrypt']
    """
    last_word = None
    for word in words:
        if word != last_word:
            yield word
        last_word = word


def convert_package_name(python_package_name, name_prefix=None, extras=()):
    """
    Convert a Python package name to a Debian package name.

    :param python_package_name: The name of a Python package as found on PyPI (a string).
    :param name_prefix: The name prefix to apply (a string or :data:`None`, in
                        which case the result of :func:`default_name_prefix()`
                        is used instead).
    :returns: A Debian package name (a string).
    """
    # Apply the name prefix.
    if not name_prefix:
        name_prefix = default_name_prefix()
    debian_package_name = '%s-%s' % (name_prefix, python_package_name)
    # Normalize casing and special characters.
    debian_package_name = normalize_package_name(debian_package_name)
    # Compact repeating words (to avoid package names like 'python-python-debian').
    debian_package_name = '-'.join(compact_repeating_words(debian_package_name.split('-')))
    # If a requirement includes extras this changes the dependencies of the
    # package. Because Debian doesn't have this concept we encode the names of
    # the extras in the name of the package.
    if extras:
        words = [debian_package_name]
        words.extend(sorted(extra.lower() for extra in extras))
        debian_package_name = '-'.join(words)
    return debian_package_name


def default_name_prefix():
    """
    Get the default package name prefix for the Python version we're running.

    :returns: One of the strings ``python``, ``python3`` or ``pypy``.
    """
    implementation = 'pypy' if platform.python_implementation() == 'PyPy' else 'python'
    if sys.version_info[0] == 3:
        implementation += '3'
    return implementation


def detect_python_script(handle):
    """
    Detect whether a file-like object contains an executable Python script.

    :param handle: A file-like object (assumed to contain an executable).
    :returns: :data:`True` if the program name in the shebang_ of the script
              references a known Python interpreter, :data:`False` otherwise.
    """
    command = extract_shebang_command(handle)
    program = extract_shebang_program(command)
    return PYTHON_EXECUTABLE_PATTERN.match(program) is not None


def embed_install_prefix(handle, install_prefix):
    """
    Embed Python snippet that adds custom installation prefix to module search path.

    :param handle: A file-like object containing an executable Python script.
    :param install_prefix: The pathname of the custom installation prefix (a string).
    :returns: A file-like object containing the modified Python script.
    """
    # Make sure the first line of the file contains something that looks like a
    # Python hashbang so we don't try to embed Python code in files like shell
    # scripts :-).
    if detect_python_script(handle):
        lines = handle.readlines()
        # We need to choose where to inject our line into the Python script.
        # This is trickier than it might seem at first, because of conflicting
        # concerns:
        #
        # 1) We want our line to be the first one to be executed so that any
        #    later imports respect the custom installation prefix.
        #
        # 2) Our line cannot be the very first line because we would break the
        #    hashbang of the script, without which it won't be executable.
        #
        # 3) Python has the somewhat obscure `from __future__ import ...'
        #    statement which must precede all other statements.
        #
        # Our first step is to skip all comments, taking care of point two.
        insertion_point = 0
        while insertion_point < len(lines) and lines[insertion_point].startswith(b'#'):
            insertion_point += 1
        # The next step is to bump the insertion point if we find any `from
        # __future__ import ...' statements.
        for i, line in enumerate(lines):
            if re.match(b'^\\s*from\\s+__future__\\s+import\\s+', line):
                insertion_point = i + 1
        lines.insert(insertion_point, ('import sys; sys.path.insert(0, %r)\n' % install_prefix).encode('UTF-8'))
        # Turn the modified contents back into a file-like object.
        handle = BytesIO(b''.join(lines))
    else:
        # Reset the file pointer of handle, so its contents can be read again later.
        handle.seek(0)
    return handle


def extract_shebang_command(handle):
    """
    Extract the shebang_ command line from an executable script.

    :param handle: A file-like object (assumed to contain an executable).
    :returns: The command in the shebang_ line (a string).

    The seek position is expected to be at the start of the file and will be
    reset afterwards, before this function returns. It is not an error if the
    executable contains binary data.

    .. _shebang: https://en.wikipedia.org/wiki/Shebang_(Unix)
    """
    try:
        if handle.read(2) == b'#!':
            data = handle.readline()
            text = data.decode('UTF-8')
            return text.strip()
        else:
            return ''
    finally:
        handle.seek(0)


def extract_shebang_program(command):
    """
    Extract the program name from a shebang_ command line.

    :param command: The result of :func:`extract_shebang_command()`.
    :returns: The program name in the shebang_ command line (a string).
    """
    tokens = shlex.split(command)
    if len(tokens) >= 2 and os.path.basename(tokens[0]) == 'env':
        tokens = tokens[1:]
    return os.path.basename(tokens[0]) if tokens else ''


def normalize_package_name(python_package_name):
    """
    Normalize Python package name to be used as Debian package name.

    :param python_package_name: The name of a Python package
                                as found on PyPI (a string).
    :returns: The normalized name (a string).

    >>> from py2deb import normalize_package_name
    >>> normalize_package_name('MySQL-python')
    'mysql-python'
    >>> normalize_package_name('simple_json')
    'simple-json'
    """
    return re.sub('[^a-z0-9]+', '-', python_package_name.lower()).strip('-')


def normalize_package_version(python_package_version, prerelease_workaround=True):
    """
    Normalize Python package version to be used as Debian package version.

    :param python_package_version: The version of a Python package (a string).
    :param prerelease_workaround: :data:`True` to enable the pre-release
                                  handling documented below, :data:`False` to
                                  restore the old behavior.

    Reformats Python package versions to comply with the Debian policy manual.
    All characters except alphanumerics, dot (``.``) and plus (``+``) are
    replaced with dashes (``-``).

    The PEP 440 pre-release identifiers 'a', 'b', 'c' and 'rc' are prefixed by
    a tilde (``~``) to replicate the intended ordering in Debian versions, also
    the identifier 'c' is translated into 'rc'. Refer to `issue #8
    <https://github.com/paylogic/py2deb/issues/8>`_ for details.
    """
    # We need to avoid normalizing "local version labels" (naming from PEP 440)
    # because these may contain strings such as SCM hashes that should not be
    # altered, so we split the version string into the "public version
    # identifier" and "local version label" and only apply normalization to the
    # "public version identifier".
    public_version, delimiter, local_version = python_package_version.partition('+')
    # Lowercase and remove invalid characters from the "public version identifier".
    public_version = re.sub('[^a-z0-9.+]+', '-', public_version.lower()).strip('-')
    if prerelease_workaround:
        # Translate the PEP 440 pre-release identifier 'c' to 'rc'.
        public_version = re.sub(r'(\d)c(\d)', r'\1rc\2', public_version)
        # Replicate the intended ordering of PEP 440 pre-release versions (a, b, rc).
        public_version = re.sub(r'(\d)(a|b|rc)(\d)', r'\1~\2\3', public_version)
    # Restore the local version label (without any normalization).
    if local_version:
        public_version = public_version + '+' + local_version
    # Make sure the "Debian revision" contains a digit. If we don't find one we
    # add it ourselves, to prevent dpkg and apt from aborting (!) as soon as
    # they see an invalid Debian revision...
    if '-' in public_version:
        components = public_version.split('-')
        if len(components) > 1 and not re.search('[0-9]', components[-1]):
            components.append('1')
            public_version = '-'.join(components)
    return public_version


def package_names_match(a, b):
    """
    Check whether two Python package names are equal.

    Uses :func:`normalize_package_name()` to normalize both names before
    comparing them for equality. This makes sure differences in case and dashes
    versus underscores are ignored.

    :param a: The name of the first Python package (a string).
    :param b: The name of the second Python package (a string).
    :returns: ``True`` if the package names match, ``False`` if they don't.
    """
    return normalize_package_name(a) == normalize_package_name(b)


def python_version():
    """
    Find the version of Python we're running.

    This specifically returns a name that matches both of the following:

    - The name of the Debian package providing the current Python version.
    - The name of the interpreter executable for the current Python version.

    :returns: A string like ``python2.7``, ``python3.8``, ``pypy`` or ``pypy3``.
    """
    if platform.python_implementation() == 'PyPy':
        python_version = 'pypy'
        if sys.version_info[0] == 3:
            python_version += '3'
    else:
        python_version = 'python%d.%d' % sys.version_info[:2]
    logger.debug("Detected Python version: %s", python_version)
    return python_version


def tokenize_version(version_number):
    """
    Tokenize a string containing a version number.

    :param version_number: The string to tokenize.
    :returns: A list of strings.
    """
    return [t for t in integer_pattern.split(version_number) if t]
