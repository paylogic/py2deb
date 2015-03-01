# Automated tests for the `py2deb' package.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: March 1, 2015
# URL: https://py2deb.readthedocs.org

"""
The :py:mod:`py2deb.tests` module contains the automated tests for `py2deb`.

The makefile in the py2deb git repository uses pytest_ to run the test suite
because of pytest's great error reporting. Nevertheless the test suite is
written to be compatible with the :py:mod:`unittest` module (part of Python's
standard library) so that the test suite can be run without additional external
dependencies.

.. _pytest: http://pytest.org/latest/goodpractises.html
"""

# Standard library modules.
import fnmatch
import functools
import glob
import logging
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

# External dependencies.
import coloredlogs
from deb_pkg_tools.checks import DuplicateFilesFound
from deb_pkg_tools.control import load_control_file
from deb_pkg_tools.package import inspect_package, parse_filename
from executor import execute

# Modules included in our package.
from py2deb.cli import main
from py2deb.converter import PackageConverter
from py2deb.utils import normalize_package_version, TemporaryDirectory

# Initialize a logger.
logger = logging.getLogger(__name__)
execute = functools.partial(execute, logger=logger)

# Global state of the test suite (yes, this is ugly :-).
TEMPORARY_DIRECTORIES = []


def setUpModule():
    """
    Prepare the test suite.

    This function does two things:

    1. Sets up verbose logging to the terminal. When a test fails the logging
       output can help to perform a post-mortem analysis of the failure in
       question (even when its hard to reproduce locally). This is especially
       useful when debugging remote test failures, whether they happened on
       Travis CI or a user's local system.

    2. Creates temporary directories where the pip download cache and the
       pip-accel binary cache are located. Isolating the pip-accel binary cache
       from the user's system is meant to ensure that the tests are as
       independent from the user's system as possible. The function
       :py:func:`tearDownModule` is responsible for cleaning up the temporary
       directory after the test suite finishes.
    """
    # Initialize verbose logging to the terminal.
    coloredlogs.install()
    coloredlogs.increase_verbosity()
    # Create temporary directories to store the pip download cache and
    # pip-accel's binary cache, to make sure these tests run isolated from the
    # rest of the system.
    os.environ['PIP_DOWNLOAD_CACHE'] = create_temporary_directory()
    os.environ['PIP_ACCEL_CACHE'] = create_temporary_directory()


def tearDownModule():
    """
    Clean up temporary directories created by :py:func:`setUpModule()`.
    """
    for directory in TEMPORARY_DIRECTORIES:
        shutil.rmtree(directory)


def create_temporary_directory():
    """
    Create a temporary directory for the test suite to use.

    The created temporary directory will be cleaned up by
    :py:func:`tearDownModule()` when the test suite is being torn down.

    :returns: The pathname of the created temporary directory (a string).
    """
    temporary_directory = tempfile.mkdtemp()
    TEMPORARY_DIRECTORIES.append(temporary_directory)
    return temporary_directory


class PackageConverterTestCase(unittest.TestCase):

    """
    :py:mod:`unittest` compatible container for the test suite of `py2deb`.
    """

    def test_argument_validation(self):
        """
        Test argument validation done by setters of :py:class:`py2deb.converter.PackageConverter`.
        """
        converter = PackageConverter()
        self.assertRaises(ValueError, converter.set_repository, '/foo/bar/baz')
        self.assertRaises(ValueError, converter.set_name_prefix, '')
        self.assertRaises(ValueError, converter.rename_package, 'old-name', '')
        self.assertRaises(ValueError, converter.rename_package, '', 'new-name')
        self.assertRaises(ValueError, converter.set_install_prefix, '')
        self.assertRaises(ValueError, converter.install_alternative, 'link', '')
        self.assertRaises(ValueError, converter.install_alternative, '', 'path')
        self.assertRaises(ValueError, converter.set_conversion_command, 'package-name', '')
        self.assertRaises(ValueError, converter.set_conversion_command, '', 'command')
        self.assertRaises(SystemExit, py2deb, '--unsupported-option')
        self.assertRaises(SystemExit, py2deb, '--report-dependencies', '/tmp/definitely-not-an-existing-control-file')
        os.environ['PY2DEB_CONFIG'] = '/tmp/definitely-not-an-existing-configuration-file'
        try:
            self.assertRaises(SystemExit, py2deb)
        finally:
            del os.environ['PY2DEB_CONFIG']

    def test_version_reformatting(self):
        """
        Test reformatting of Python version strings.
        """
        assert normalize_package_version('1.5_42') == '1.5-42'
        assert normalize_package_version('1.5-whatever') == '1.5-whatever-1'

    def test_conversion_of_simple_package(self):
        """
        Convert a simple Python package without any dependencies.

        Converts coloredlogs_ and sanity checks the result. Performs several static
        checks on the metadata and contents of the resulting package archive.

        .. _coloredlogs: https://pypi.python.org/pypi/coloredlogs
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            # Run the conversion twice to check that existing archives are not overwritten.
            last_modified_time = 0
            for i in range(2):
                # Prepare a control file to be patched.
                control_file = os.path.join(directory, 'control')
                with open(control_file, 'w') as handle:
                    handle.write('Depends: vim\n')
                # Run the conversion command.
                py2deb('--verbose',
                       '--yes',
                       '--repository=%s' % directory,
                       '--report-dependencies=%s' % control_file,
                       'coloredlogs==0.5')
                # Check that the control file was patched.
                control_fields = load_control_file(control_file)
                assert control_fields['Depends'].matches('vim')
                assert control_fields['Depends'].matches('python-coloredlogs', '0.5')
                # Find the generated Debian package archive.
                archives = glob.glob('%s/*.deb' % directory)
                logger.debug("Found generated archive(s): %s", archives)
                assert len(archives) == 1
                # Verify that existing archives are not overwritten.
                if not last_modified_time:
                    # Capture the last modified time of the archive in the first iteration.
                    last_modified_time = os.path.getmtime(archives[0])
                else:
                    # Verify the last modified time of the archive in the second iteration.
                    assert last_modified_time == os.path.getmtime(archives[0])
                # Use deb-pkg-tools to inspect the generated package.
                metadata, contents = inspect_package(archives[0])
                logger.debug("Metadata of generated package: %s", dict(metadata))
                logger.debug("Contents of generated package: %s", dict(contents))
                # Check the package metadata.
                assert metadata['Package'] == 'python-coloredlogs'
                assert metadata['Version'].startswith('0.5')
                assert metadata['Architecture'] == 'all'
                # There should be exactly one dependency: some version of Python.
                assert metadata['Depends'].matches('python%i.%i' % sys.version_info[:2])
                # Don't care about the format here as long as essential information is retained.
                assert 'Peter Odding' in metadata['Maintainer']
                assert 'peter@peterodding.com' in metadata['Maintainer']
                # Check the package contents.
                # Check for the two *.py files that should be installed by the package.
                assert find_file(contents, '/usr/lib/python*/dist-packages/coloredlogs/__init__.py')
                assert find_file(contents, '/usr/lib/python*/dist-packages/coloredlogs/converter.py')
                # Make sure the file ownership and permissions are sane.
                archive_entry = find_file(contents, '/usr/lib/python*/dist-packages/coloredlogs/__init__.py')
                assert archive_entry.owner == 'root'
                assert archive_entry.group == 'root'
                assert archive_entry.permissions == '-rw-r--r--'

    def test_custom_conversion_command(self):
        """
        Convert a simple Python package that requires a custom conversion command.

        Converts Fabric and sanity checks the result. For details please refer
        to :py:func:`py2deb.converter.PackageConverter.set_conversion_command()`.
        """
        if sys.version_info[0] == 3:
            logger.warning("Skipping Fabric conversion test! (Fabric is not Python 3.x compatible)")
            return
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = PackageConverter()
            converter.set_repository(directory)
            converter.set_conversion_command('Fabric', 'rm -Rf paramiko')
            converter.convert(['Fabric==0.9.0'])
            # Find the generated Debian package archive.
            archives = glob.glob('%s/*.deb' % directory)
            logger.debug("Found generated archive(s): %s", archives)
            pathname = find_package_archive(archives, 'python-fabric')
            # Use deb-pkg-tools to inspect the generated package.
            metadata, contents = inspect_package(pathname)
            # Check for the two *.py files that should be installed by the package.
            for filename, entry in contents.items():
                if filename.startswith('/usr/lib') and not entry.permissions.startswith('d'):
                    assert 'fabric' in filename.lower()
                    assert 'paramiko' not in filename.lower()

    def test_duplicate_files_check(self):
        """
        Ensure that `py2deb` checks for duplicate file conflicts within dependency sets.

        Converts a version of Fabric that bundles Paramiko but also includes
        Paramiko itself in the dependency set, thereby causing a duplicate file
        conflict, to verify that `py2deb` recognizes duplicate file conflicts.
        """
        if sys.version_info[0] == 3:
            logger.warning("Skipping Fabric conversion test! (Fabric is not Python 3.x compatible)")
            return
        with TemporaryDirectory() as directory:
            converter = PackageConverter()
            converter.set_repository(directory)
            self.assertRaises(DuplicateFilesFound,
                              converter.convert,
                              ['Fabric==0.9.0', 'Paramiko==1.14.0'])

    def test_conversion_of_package_with_dependencies(self):
        """
        Convert a non trivial Python package with several dependencies.

        Converts deb-pkg-tools_ to a Debian package archive and sanity checks the
        result. Performs static checks on the metadata (dependencies) of the
        resulting package archive.

        .. _deb-pkg-tools: https://pypi.python.org/pypi/deb-pkg-tools
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            py2deb('--repository=%s' % directory, 'deb-pkg-tools==1.22')
            # Find the generated Debian package archives.
            archives = glob.glob('%s/*.deb' % directory)
            logger.debug("Found generated archive(s): %s", archives)
            # Make sure the expected dependencies have been converted.
            assert sorted(parse_filename(a).name for a in archives) == sorted([
                'python-cached-property',
                'python-chardet',
                'python-coloredlogs',
                'python-deb-pkg-tools',
                'python-debian',
                'python-executor',
                'python-humanfriendly',
                'python-six',
            ])
            # Use deb-pkg-tools to inspect ... deb-pkg-tools :-)
            pathname = find_package_archive(archives, 'python-deb-pkg-tools')
            metadata, contents = inspect_package(pathname)
            logger.debug("Metadata of generated package: %s", dict(metadata))
            logger.debug("Contents of generated package: %s", dict(contents))
            # Make sure the dependencies defined in `stdeb.cfg' have been preserved.
            for configured_dependency in ['apt', 'apt-utils', 'dpkg-dev', 'fakeroot', 'gnupg', 'lintian']:
                logger.debug("Checking configured dependency %s ..", configured_dependency)
                assert metadata['Depends'].matches(configured_dependency) is not None
            # Make sure the dependencies defined in `setup.py' have been preserved.
            expected_dependencies = [
                'python-chardet', 'python-coloredlogs', 'python-debian',
                'python-executor', 'python-humanfriendly'
            ]
            for python_dependency in expected_dependencies:
                logger.debug("Checking Python dependency %s ..", python_dependency)
                assert metadata['Depends'].matches(python_dependency) is not None

    def test_conversion_of_extras(self):
        """
        Convert a package with extras.

        Converts ``raven[flask]==3.6.0`` and sanity checks the result.
        """
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = PackageConverter()
            converter.set_repository(directory)
            archives, relationships = converter.convert(['raven[flask]==3.6.0'])
            # Check that a relationship with the extra in the package name was generated.
            assert relationships == ['python-raven-flask (= 3.6.0)']
            # Check that a package with the extra in the filename was generated.
            assert find_package_archive(archives, 'python-raven-flask')

    def test_conversion_of_binary_package(self):
        """
        Convert a package that includes a ``*.so`` file (a shared object file).

        Converts ``setproctitle==1.1.8`` and sanity checks the result. The goal
        of this test is to verify that pydeb properly handles packages with
        binary components (including dpkg-shlibdeps_ magic). This explains why
        I chose the setproctitle_ package:

        1. This package is known to require a compiled shared object file for
           proper functioning.

        2. Despite requiring a compiled shared object file the package is
           fairly lightweight and has little dependencies so including this
           test on every run of the test suite won't slow things down so much
           that it becomes annoying.

        3. The package is documented to support Python 3.x as well which means
           we can run this test on all supported Python versions.

        .. _dpkg-shlibdeps: http://man.he.net/man1/dpkg-shlibdeps
        .. _setproctitle: https://pypi.python.org/pypi/setproctitle/
        """
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = PackageConverter()
            converter.set_repository(directory)
            archives, relationships = converter.convert(['setproctitle==1.1.8'])
            # Find the generated *.deb archive.
            pathname = find_package_archive(archives, 'python-setproctitle')
            # Use deb-pkg-tools to inspect the package metadata.
            metadata, contents = inspect_package(pathname)
            logger.debug("Metadata of generated package: %s", dict(metadata))
            logger.debug("Contents of generated package: %s", dict(contents))
            # Make sure the package's architecture was properly set.
            assert metadata['Architecture'] != 'all'
            # Make sure the shared object file is included in the package.
            assert find_file(contents, '/usr/lib/*/setproctitle*.so')
            # Make sure a dependency on libc was added (this shows that
            # dpkg-shlibdeps was run successfully).
            assert 'libc6' in metadata['Depends'].names

    def test_conversion_of_isolated_packages(self):
        """
        Convert a group of packages with a custom name and installation prefix.

        Converts pip-accel_ and its dependencies to a group of "isolated Debian
        packages" that are installed with a custom name prefix and installation
        prefix and sanity check the result. Also tests the ``--rename=FROM,TO``
        command line option. Performs static checks on the metadata and contents of
        the resulting package archive.
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            py2deb('--repository=%s' % directory,
                   '--name-prefix=pip-accel',
                   '--install-prefix=/usr/lib/pip-accel',
                   # By default py2deb will generate a package called
                   # `pip-accel-pip-accel'. The --no-name-prefix=PKG
                   # option can be used to avoid this.
                   '--no-name-prefix=pip-accel',
                   # Strange but valid use case (renaming a dependency):
                   # pip-accel-coloredlogs -> pip-accel-coloredlogs-renamed
                   '--rename=coloredlogs,pip-accel-coloredlogs-renamed',
                   # Also test the update-alternatives integration.
                   '--install-alternative=/usr/bin/pip-accel,/usr/lib/pip-accel/bin/pip-accel',
                   'pip-accel==0.12.6')
            # Check the results.
            self.check_converted_pip_accel_packages(directory)

    def test_conversion_with_configuration_file(self):
        """
        Convert a group of packages based on the settings in a configuration file.

        Repeats the same test as :py:func:`test_conversion_of_isolated_packages()`
        but instead of using command line options the conversion process is
        configured using a configuration file.
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            configuration_file = os.path.join(directory, 'py2deb.ini')
            with open(configuration_file, 'w') as handle:
                handle.write(format('''
                    [py2deb]
                    repository = {repository}
                    name-prefix = pip-accel
                    install-prefix = /usr/lib/pip-accel
                    auto-install = false

                    [alternatives]
                    /usr/bin/pip-accel = /usr/lib/pip-accel/bin/pip-accel

                    [package:pip-accel]
                    no-name-prefix = true

                    [package:coloredlogs]
                    rename = pip-accel-coloredlogs-renamed
                ''', repository=directory))
            # Run the conversion command.
            py2deb('--config=%s' % configuration_file, 'pip-accel==0.12.6')
            # Check the results.
            self.check_converted_pip_accel_packages(directory)

    def check_converted_pip_accel_packages(self, directory):
        """
        Check a group of packages converted with a custom name and installation prefix.

        Check the results of :py:func:`test_conversion_of_isolated_packages()` and
        :py:func:`test_conversion_with_configuration_file()`.
        """
        # Find the generated Debian package archives.
        archives = glob.glob('%s/*.deb' % directory)
        logger.debug("Found generated archive(s): %s", archives)
        # Make sure the expected dependencies have been converted.
        assert sorted(parse_filename(a).name for a in archives) == sorted([
            'pip-accel',
            'pip-accel-coloredlogs-renamed',
            'pip-accel-humanfriendly',
            'pip-accel-pip',
        ])
        # Use deb-pkg-tools to inspect pip-accel.
        pathname = find_package_archive(archives, 'pip-accel')
        metadata, contents = inspect_package(pathname)
        logger.debug("Metadata of generated package: %s", dict(metadata))
        logger.debug("Contents of generated package: %s", dict(contents))
        # Make sure the dependencies defined in `setup.py' have been
        # preserved while their names have been converted.
        assert metadata['Depends'].matches('pip-accel-coloredlogs-renamed', '0.4.6')
        assert metadata['Depends'].matches('pip-accel-humanfriendly', '1.6')
        assert metadata['Depends'].matches('pip-accel-pip', '1.4')
        assert not metadata['Depends'].matches('pip-accel-pip', '1.3')
        assert not metadata['Depends'].matches('pip-accel-pip', '1.5')
        # Make sure the executable script has been installed and is marked as executable.
        pip_accel_executable = find_file(contents, '/usr/lib/pip-accel/bin/pip-accel')
        assert pip_accel_executable.permissions == '-rwxr-xr-x'
        # Verify the existence of some expected files (picked more or less at random).
        assert find_file(contents, '/usr/lib/pip-accel/lib/pip_accel/__init__.py')
        assert find_file(contents, '/usr/lib/pip-accel/lib/pip_accel/deps/debian.ini')
        assert find_file(contents, '/usr/lib/pip-accel/lib/pip_accel-0.12.6*.egg-info/PKG-INFO')
        # Verify that all files are installed in the custom installation
        # prefix. We have to ignore directories, otherwise we would start
        # complaining about the parent directories /, /usr, /usr/lib, etc.
        for filename, properties in contents.items():
            is_directory = properties.permissions.startswith('d')
            in_isolated_directory = filename.startswith('/usr/lib/pip-accel/')
            assert is_directory or in_isolated_directory


def py2deb(*arguments):
    """
    Test everything including command line parsing by running py2deb's main function.

    We want the test suite to cover as much of `py2deb` as possible, so
    including the command line interface, however we don't want to run `py2deb`
    as a subprocess because that would break test coverage measurements. This
    explains the purpose of the :py:func:`py2deb()` function.

    :param arguments: The command line arguments to pass to `py2deb` (one or more strings).
    """
    sys.argv[1:] = arguments
    main()


def find_package_archive(available_archives, package_name):
    """
    Find the ``*.deb`` archive of a specific package.

    :param available_packages: The pathnames of the available package archives
                               (a list of strings).
    :param package_name: The name of the package whose archive file we're
                         interested in (a string).
    :returns: The pathname of the package archive (a string).
    :raises: :py:exc:`exceptions.AssertionError` if zero or more than one
             package archive is found.
    """
    matches = []
    for pathname in available_archives:
        if parse_filename(pathname).name == package_name:
            matches.append(pathname)
    assert len(matches) == 1, "Expected to match exactly one package archive!"
    return matches[0]


def find_file(contents, pattern):
    """
    Find the file matching the given filename pattern.

    Searches the dictionary of Debian package archive entries reported by
    :py:func:`deb_pkg_tools.package.inspect_package()`.

    :param contents: The dictionary of package archive entries.
    :param pattern: The filename pattern to match (:py:mod:`fnmatch` syntax).
    :returns: The metadata of the matched file.
    :raises: :py:exc:`exceptions.AssertionError` if zero or more than one
             archive entry is found.
    """
    matches = []
    for filename, metadata in contents.items():
        if fnmatch.fnmatch(filename, pattern):
            matches.append(metadata)
    assert len(matches) == 1, "Expected to match exactly one archive entry!"
    return matches[0]


def format(text, **kw):
    """
    Dedent, strip and format a multiline string with format specifications.

    :param text: The text to format (a string).
    :param kw: Any format string arguments.
    :returns: The formatted text (a string).
    """
    return textwrap.dedent(text).strip().format(**kw)
