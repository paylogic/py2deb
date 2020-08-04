# Automated tests for the `py2deb' package.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: August 4, 2020
# URL: https://py2deb.readthedocs.io

"""
The :mod:`py2deb.tests` module contains the automated tests for `py2deb`.

The makefile in the py2deb git repository uses pytest_ to run the test suite
because of pytest's great error reporting. Nevertheless the test suite is
written to be compatible with the :mod:`unittest` module (part of Python's
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

# External dependencies.
import coloredlogs
from deb_pkg_tools.checks import DuplicateFilesFound
from deb_pkg_tools.control import load_control_file, patch_control_file
from deb_pkg_tools.package import inspect_package, parse_filename
from executor import execute
from humanfriendly.text import dedent
from humanfriendly.testing import TestCase, run_cli

# Modules included in our package.
from py2deb.cli import main
from py2deb.converter import PackageConverter
from py2deb.utils import (
    TemporaryDirectory,
    convert_package_name,
    default_name_prefix,
    normalize_package_version,
    python_version,
)
from py2deb.hooks import (
    cleanup_bytecode_files,
    cleanup_namespaces,
    find_bytecode_files,
    find_installed_files,
    generate_bytecode_files,
    HAS_PEP_3147,
    initialize_namespaces,
    post_installation_hook,
    pre_removal_hook,
    touch,
)

# Initialize a logger.
logger = logging.getLogger(__name__)
execute = functools.partial(execute, logger=logger)

# Global state of the test suite (yes, this is ugly :-).
TEMPORARY_DIRECTORIES = []

# Data structure used by namespace tests.
TEST_NAMESPACES = [('foo',),
                   ('foo', 'bar'),
                   ('foo', 'bar', 'baz')]


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
       :func:`tearDownModule` is responsible for cleaning up the temporary
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
    """Clean up temporary directories created by :func:`setUpModule()`."""
    for directory in TEMPORARY_DIRECTORIES:
        shutil.rmtree(directory)


def create_temporary_directory():
    """
    Create a temporary directory for the test suite to use.

    The created temporary directory will be cleaned up by
    :func:`tearDownModule()` when the test suite is being torn down.

    :returns: The pathname of the created temporary directory (a string).
    """
    temporary_directory = tempfile.mkdtemp()
    TEMPORARY_DIRECTORIES.append(temporary_directory)
    return temporary_directory


class PackageConverterTestCase(TestCase):

    """:mod:`unittest` compatible container for the test suite of `py2deb`."""

    def create_isolated_converter(self):
        """Instantiate an isolated package converter."""
        return PackageConverter(load_configuration_files=False,
                                load_environment_variables=False)

    def test_argument_validation(self):
        """Test argument validation done by setters of :class:`py2deb.converter.PackageConverter`."""
        converter = self.create_isolated_converter()
        self.assertRaises(ValueError, converter.set_repository, '/foo/bar/baz')
        self.assertRaises(ValueError, converter.set_name_prefix, '')
        self.assertRaises(ValueError, converter.rename_package, 'old-name', '')
        self.assertRaises(ValueError, converter.rename_package, '', 'new-name')
        self.assertRaises(ValueError, converter.set_install_prefix, '')
        self.assertRaises(ValueError, converter.install_alternative, 'link', '')
        self.assertRaises(ValueError, converter.install_alternative, '', 'path')
        self.assertRaises(ValueError, converter.set_conversion_command, 'package-name', '')
        self.assertRaises(ValueError, converter.set_conversion_command, '', 'command')
        exit_code, output = run_cli(main, '--unsupported-option')
        assert exit_code != 0
        exit_code, output = run_cli(main, '--report-dependencies', '/tmp/definitely-not-an-existing-control-file')
        assert exit_code != 0
        os.environ['PY2DEB_CONFIG'] = '/tmp/definitely-not-an-existing-configuration-file'
        try:
            exit_code, output = run_cli(main)
            assert exit_code != 0
        finally:
            del os.environ['PY2DEB_CONFIG']

    def test_version_reformatting(self):
        """Test reformatting of Python version strings."""
        assert normalize_package_version('1.5_42') == '1.5-42'
        assert normalize_package_version('1.5-whatever') == '1.5-whatever-1'
        # PEP 440 pre-release versions (specific handling added in release 1.0).
        assert normalize_package_version('1.0a2') == '1.0~a2'
        assert normalize_package_version('1.0b2') == '1.0~b2'
        assert normalize_package_version('1.0c2') == '1.0~rc2'
        assert normalize_package_version('1.0rc2') == '1.0~rc2'
        # Do not modify local version labels
        assert normalize_package_version('1.0+a2') == '1.0+a2'
        assert normalize_package_version('1.0+b2') == '1.0+b2'
        assert normalize_package_version('1.0+c2') == '1.0+c2'
        assert normalize_package_version('1.0+65c43') == '1.0+65c43'
        # New versus old behavior (the option to control backwards compatibility was added in release 2.1).
        assert normalize_package_version('1.0a2', prerelease_workaround=True) == '1.0~a2'
        assert normalize_package_version('1.0a2', prerelease_workaround=False) == '1.0a2'

    def test_conversion_of_simple_package(self):
        """
        Convert a simple Python package without any dependencies.

        Converts coloredlogs_ and sanity checks the result. Performs several static
        checks on the metadata and contents of the resulting package archive.

        .. _coloredlogs: https://pypi.org/project/coloredlogs
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
                exit_code, output = run_cli(
                    main,
                    '--verbose',
                    '--yes',
                    '--repository=%s' % directory,
                    '--report-dependencies=%s' % control_file,
                    'coloredlogs==0.5',
                )
                assert exit_code == 0
                # Check that the control file was patched.
                control_fields = load_control_file(control_file)
                assert control_fields['Depends'].matches('vim')
                assert control_fields['Depends'].matches(fix_name_prefix('python-coloredlogs'), '0.5')
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
                assert metadata['Package'] == fix_name_prefix('python-coloredlogs')
                assert metadata['Version'].startswith('0.5')
                assert metadata['Architecture'] == 'all'
                # There should be exactly one dependency: some version of Python.
                assert metadata['Depends'].matches(python_version())
                # Don't care about the format here as long as essential information is retained.
                assert 'Peter Odding' in metadata['Maintainer']
                assert 'peter@peterodding.com' in metadata['Maintainer']
                # Check the package contents.
                # Check for the two *.py files that should be installed by the package.
                assert find_file(contents, '/usr/lib/py*/dist-packages/coloredlogs/__init__.py')
                assert find_file(contents, '/usr/lib/py*/dist-packages/coloredlogs/converter.py')
                # Make sure the file ownership and permissions are sane.
                archive_entry = find_file(contents, '/usr/lib/py*/dist-packages/coloredlogs/__init__.py')
                assert archive_entry.owner == 'root'
                assert archive_entry.group == 'root'
                assert archive_entry.permissions == '-rw-r--r--'

    def test_custom_conversion_command(self):
        """
        Convert a simple Python package that requires a custom conversion command.

        Converts Fabric and sanity checks the result. For details please refer
        to :func:`py2deb.converter.PackageConverter.set_conversion_command()`.
        """
        if sys.version_info[0] == 3:
            self.skipTest("Fabric is not Python 3.x compatible")
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            converter.set_conversion_command('Fabric', 'rm -Rf paramiko')
            converter.convert(['--no-deps', 'Fabric==0.9.0'])
            # Find the generated Debian package archive.
            archives = glob.glob('%s/*.deb' % directory)
            logger.debug("Found generated archive(s): %s", archives)
            pathname = find_package_archive(archives, fix_name_prefix('python-fabric'))
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
            self.skipTest("Fabric is not Python 3.x compatible")
        with TemporaryDirectory() as directory:
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            self.assertRaises(
                DuplicateFilesFound,
                converter.convert,
                ['--no-deps', 'Fabric==0.9.0', 'Paramiko==1.14.0'],
            )

    def test_conversion_of_package_with_dependencies(self):
        """
        Convert a non trivial Python package with several dependencies.

        Converts deb-pkg-tools_ to a Debian package archive and sanity checks the
        result. Performs static checks on the metadata (dependencies) of the
        resulting package archive.

        .. _deb-pkg-tools: https://pypi.org/project/deb-pkg-tools
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            exit_code, output = run_cli(main, '--repository=%s' % directory, 'deb-pkg-tools==1.22')
            assert exit_code == 0
            # Find the generated Debian package archives.
            archives = glob.glob('%s/*.deb' % directory)
            logger.debug("Found generated archive(s): %s", archives)
            # Make sure the expected dependencies have been converted.
            converted_dependencies = set(parse_filename(a).name for a in archives)
            expected_dependencies = set(convert_package_name(n) for n in (
                'cached-property',
                'chardet',
                'coloredlogs',
                'deb-pkg-tools',
                'executor',
                'humanfriendly',
                'python-debian',
                'six',
            ))
            assert expected_dependencies.issubset(converted_dependencies)
            # Use deb-pkg-tools to inspect ... deb-pkg-tools :-)
            pathname = find_package_archive(archives, fix_name_prefix('python-deb-pkg-tools'))
            metadata, contents = inspect_package(pathname)
            logger.debug("Metadata of generated package: %s", dict(metadata))
            logger.debug("Contents of generated package: %s", dict(contents))
            # Make sure the dependencies defined in `stdeb.cfg' have been preserved.
            for configured_dependency in ['apt', 'apt-utils', 'dpkg-dev', 'fakeroot', 'gnupg', 'lintian']:
                logger.debug("Checking configured dependency %s ..", configured_dependency)
                assert metadata['Depends'].matches(configured_dependency) is not None
            # Make sure the dependencies defined in `setup.py' have been preserved.
            expected_dependencies = [convert_package_name(n) for n in (
                'chardet', 'coloredlogs', 'executor', 'humanfriendly', 'python-debian',
            )]
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
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            archives, relationships = converter.convert([
                # Flask 1.0 drops Python 2.6 compatibility so we explicitly
                # include an older version to prevent raven[flask] from pulling
                # in the latest version of flask, causing this test to fail.
                'flask==0.12.4',
                'raven[flask]==3.6.0',
            ])
            # Check that a relationship with the extra in the package name was generated.
            expression = '%s (= 3.6.0)' % fix_name_prefix('python-raven-flask')
            assert expression in relationships
            # Check that a package with the extra in the filename was generated.
            archive = find_package_archive(archives, fix_name_prefix('python-raven-flask'))
            assert archive
            # Use deb-pkg-tools to inspect the package metadata.
            metadata, contents = inspect_package(archive)
            logger.debug("Metadata of generated package: %s", dict(metadata))
            # Check that a "Provides" field was added.
            assert metadata['Provides'].matches(fix_name_prefix('python-raven'))

    def test_conversion_of_environment_markers(self):
        """
        Convert a package with installation requirements using environment markers.

        Converts ``weasyprint==0.42`` and sanity checks that the ``cairosvg``
        dependency is present.
        """
        with TemporaryDirectory() as directory:
            # Find our constraints file.
            module_directory = os.path.dirname(os.path.abspath(__file__))
            project_directory = os.path.dirname(module_directory)
            constraints_file = os.path.join(project_directory, 'constraints.txt')
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            # Constrain tinycss2 to avoid Python 2 incompatibilities:
            # https://travis-ci.org/github/paylogic/py2deb/jobs/713388666
            archives, relationships = converter.convert(['--constraint=%s' % constraints_file, 'weasyprint==0.42'])
            # Check that the dependency is present.
            pathname = find_package_archive(archives, fix_name_prefix('python-weasyprint'))
            metadata, contents = inspect_package(pathname)
            # Make sure the dependency on cairosvg was added (this confirms
            # that environment markers have been evaluated).
            assert fix_name_prefix('python-cairosvg') in metadata['Depends'].names

    def test_python_requirements_fallback(self):
        """Test the fall-back implementation of the ``python_requirements`` property."""
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            packages = list(converter.get_source_distributions(['coloredlogs==6.0']))
            coloredlogs_package = next(p for p in packages if p.python_name == 'coloredlogs')
            assert any(p.key == 'humanfriendly' for p in coloredlogs_package.python_requirements)
            assert any(p.key == 'humanfriendly' for p in coloredlogs_package.python_requirements_fallback)

    def test_namespace_package_parsing(self):
        """Test parsing of ``namespace_package.txt`` files."""
        converter = self.create_isolated_converter()
        package = next(converter.get_source_distributions(['--no-deps', 'zope.app.cache==3.7.0']))
        assert package.namespace_packages == ['zope', 'zope.app']
        assert package.namespaces == [('zope',), ('zope', 'app')]

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

        .. _setproctitle: https://pypi.org/project/setproctitle/
        .. _dpkg-shlibdeps: https://manpages.debian.org/dpkg-shlibdeps
        """
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            archives, relationships = converter.convert(['setproctitle==1.1.8'])
            # Find the generated *.deb archive.
            pathname = find_package_archive(archives, fix_name_prefix('python-setproctitle'))
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

    def test_converted_package_installation(self):
        """
        Install a converted package on the test system and verify that it works.

        This test only runs on Travis CI, it's a functional test that uses
        py2deb to convert a Python package to a Debian package, installs
        that package on the local system and verifies that the system wide
        Python installation can successfully import the installed package.
        """
        if os.environ.get('TRAVIS') != 'true':
            self.skipTest("This test should only be run on Travis CI! (set $TRAVIS_CI=true to override)")
        with TemporaryDirectory() as directory:
            version = '1.1.8'
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            archives, relationships = converter.convert(['setproctitle==%s' % version])
            # Find and install the generated *.deb archive.
            pathname = find_package_archive(archives, fix_name_prefix('python-setproctitle'))
            execute('dpkg', '--install', pathname, sudo=True)
            # Verify that the installed package can be imported.
            interpreter = '/usr/bin/%s' % python_version()
            output = execute(interpreter, '-c', '; '.join([
                'import setproctitle',
                'print(setproctitle.__version__)',
            ]), capture=True)
            assert output == version

    def test_conversion_of_binary_package_with_executable(self):
        """
        Convert a package that includes a binary executable file.

        Converts ``uwsgi==2.0.17.1`` and sanity checks the result. The goal of
        this test is to verify that pydeb preserves binary executables instead
        of truncating them as it did until `issue 9`_ was reported.

        .. _issue 9: https://github.com/paylogic/py2deb/issues/9
        """
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(directory)
            converter.set_install_prefix('/usr/lib/py2deb/uwsgi')
            archives, relationships = converter.convert(['uwsgi==2.0.17.1'])
            # Find the generated *.deb archive.
            pathname = find_package_archive(archives, fix_name_prefix('python-uwsgi'))
            # Use deb-pkg-tools to inspect the package metadata.
            metadata, contents = inspect_package(pathname)
            logger.debug("Contents of generated package: %s", dict(contents))
            # Find the binary executable file.
            executable = find_file(contents, '/usr/lib/py2deb/uwsgi/bin/uwsgi')
            assert executable.size > 0

    def test_install_requires_version_munging(self):
        """
        Convert a package with a requirement whose version is "munged" by pip.

        Refer to :func:`py2deb.converter.PackageConverter.transform_version()`
        for details about the purpose of this test.
        """
        with TemporaryDirectory() as repository_directory:
            with TemporaryDirectory() as distribution_directory:
                # Create a temporary (and rather trivial :-) Python package.
                with open(os.path.join(distribution_directory, 'setup.py'), 'w') as handle:
                    handle.write(dedent('''
                        from setuptools import setup
                        setup(
                            name='install-requires-munging-test',
                            version='1.0',
                            install_requires=['humanfriendly==1.30.0'],
                        )
                    '''))
                # Run the conversion command.
                converter = self.create_isolated_converter()
                converter.set_repository(repository_directory)
                archives, relationships = converter.convert([distribution_directory])
                # Find the generated *.deb archive.
                pathname = find_package_archive(archives, fix_name_prefix('python-install-requires-munging-test'))
                # Use deb-pkg-tools to inspect the package metadata.
                metadata, contents = inspect_package(pathname)
                logger.debug("Metadata of generated package: %s", dict(metadata))
                logger.debug("Contents of generated package: %s", dict(contents))
                # Inspect the converted package's dependency.
                assert metadata['Depends'].matches(fix_name_prefix('python-humanfriendly'), '1.30'), \
                    "py2deb failed to rewrite version of dependency!"
                assert not metadata['Depends'].matches(fix_name_prefix('python-humanfriendly'), '1.30.0'), \
                    "py2deb failed to rewrite version of dependency!"

    def test_conversion_with_system_package(self):
        """Convert a package and map one of its requirements to a system package."""
        with TemporaryDirectory() as repository_directory:
            with TemporaryDirectory() as distribution_directory:
                # Create a temporary (and rather trivial :-) Python package.
                with open(os.path.join(distribution_directory, 'setup.py'), 'w') as handle:
                    handle.write(dedent('''
                        from setuptools import setup
                        setup(
                            name='system-package-conversion-test',
                            version='1.0',
                            install_requires=['dbus-python'],
                        )
                    '''))
                # Run the conversion command.
                converter = self.create_isolated_converter()
                converter.set_repository(repository_directory)
                converter.use_system_package('dbus-python', fix_name_prefix('python-dbus'))
                archives, relationships = converter.convert([distribution_directory])
                # Make sure only one archive was generated.
                assert len(archives) == 1
                # Use deb-pkg-tools to inspect the package metadata.
                metadata, contents = inspect_package(archives[0])
                logger.debug("Metadata of generated package: %s", dict(metadata))
                logger.debug("Contents of generated package: %s", dict(contents))
                # Inspect the converted package's dependency.
                assert metadata['Depends'].matches(fix_name_prefix('python-dbus')), \
                    "py2deb failed to rewrite dependency name!"

    def test_conversion_of_isolated_packages(self):
        """
        Convert a group of packages with a custom name and installation prefix.

        Converts pip-accel_ and its dependencies to a group of "isolated Debian
        packages" that are installed with a custom name prefix and installation
        prefix and sanity check the result. Also tests the ``--rename=FROM,TO``
        command line option. Performs static checks on the metadata and contents of
        the resulting package archive.

        .. _pip-accel: https://github.com/paylogic/pip-accel
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            # Run the conversion command.
            exit_code, output = run_cli(
                main,
                '--repository=%s' % directory,
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
                'pip-accel==0.12.6',
            )
            assert exit_code == 0
            # Check the results.
            self.check_converted_pip_accel_packages(directory)

    def test_conversion_with_configuration_file(self):
        """
        Convert a group of packages based on the settings in a configuration file.

        Repeats the same test as :func:`test_conversion_of_isolated_packages()`
        but instead of using command line options the conversion process is
        configured using a configuration file.
        """
        # Use a temporary directory as py2deb's repository directory so that we
        # can easily find the *.deb archive generated by py2deb.
        with TemporaryDirectory() as directory:
            configuration_file = os.path.join(directory, 'py2deb.ini')
            with open(configuration_file, 'w') as handle:
                handle.write(dedent('''
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
            exit_code, output = run_cli(main, '--config=%s' % configuration_file, 'pip-accel==0.12.6')
            assert exit_code == 0
            # Check the results.
            self.check_converted_pip_accel_packages(directory)

    def check_converted_pip_accel_packages(self, directory):
        """
        Check a group of packages converted with a custom name and installation prefix.

        Check the results of :func:`test_conversion_of_isolated_packages()` and
        :func:`test_conversion_with_configuration_file()`.
        """
        # Find the generated Debian package archives.
        archives = glob.glob('%s/*.deb' % directory)
        logger.debug("Found generated archive(s): %s", archives)
        # Make sure the expected dependencies have been converted.
        converted_dependencies = set(parse_filename(a).name for a in archives)
        expected_dependencies = set([
            'pip-accel',
            'pip-accel-coloredlogs-renamed',
            'pip-accel-humanfriendly',
            'pip-accel-pip',
        ])
        assert expected_dependencies.issubset(converted_dependencies)
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
        paths_to_ignore = ['/usr/share/lintian/overrides/pip-accel']
        for filename, properties in contents.items():
            if filename not in paths_to_ignore:
                is_directory = properties.permissions.startswith('d')
                in_isolated_directory = filename.startswith('/usr/lib/pip-accel/')
                assert is_directory or in_isolated_directory

    def test_python_callback_from_api(self):
        """Test Python callback logic (registered through the Python API)."""
        self.check_python_callback(python_callback_fn)

    def test_python_callback_from_dotted_path(self):
        """Test Python callback logic (through a dotted path expression)."""
        self.check_python_callback('py2deb.tests:python_callback_fn')

    def test_python_callback_from_filename(self):
        """Test Python callback logic (through a filename expression)."""
        filename = os.path.abspath(__file__)
        self.check_python_callback('%s:python_callback_fn' % filename)

    def check_python_callback(self, expression):
        """Test for Python callback logic manipulating the build of a package."""
        with TemporaryDirectory() as repository_directory:
            # Run the conversion command.
            converter = self.create_isolated_converter()
            converter.set_repository(repository_directory)
            converter.set_python_callback(expression)
            converter.set_name_prefix('callback-test')
            archives, relationships = converter.convert(['naturalsort'])
            # Find the generated *.deb archive.
            pathname = find_package_archive(archives, 'callback-test-naturalsort')
            # Use deb-pkg-tools to inspect the package metadata.
            metadata, contents = inspect_package(pathname)
            logger.debug("Metadata of generated package: %s", dict(metadata))
            logger.debug("Contents of generated package: %s", dict(contents))
            # Inspect the converted package's dependency.
            assert metadata['Breaks'].matches('callback-test-natsort'), \
                "Result of Python callback not visible?!"
            assert metadata['Replaces'].matches('callback-test-natsort'), \
                "Result of Python callback not visible?!"

    def test_find_installed_files(self):
        """Test the :func:`py2deb.hooks.find_installed_files()` function."""
        assert '/usr/bin/dpkg' in find_installed_files('dpkg'), \
            "find_installed_files() returned unexpected output for the 'dpkg' package!"

    def test_bytecode_generation(self):
        """
        Test byte code generation and cleanup.

        This tests the :func:`~py2deb.hooks.generate_bytecode_files()` and
        :func:`~py2deb.hooks.cleanup_bytecode_files()` functions.
        """
        with TemporaryDirectory() as directory:
            # Generate a Python file.
            python_file = os.path.join(directory, 'test.py')
            with open(python_file, 'w') as handle:
                handle.write('print(42)\n')
            # Generate the byte code file.
            generate_bytecode_files('bytecode-test', [python_file])
            # Make sure a byte code file was generated.
            bytecode_files = list(find_bytecode_files(python_file))
            assert len(bytecode_files) > 0 and all(os.path.isfile(fn) for fn in bytecode_files), \
                "Failed to generate Python byte code file!"
            # Sneak a random file into the __pycache__ directory to test the
            # error handling in cleanup_bytecode_files().
            cache_directory = os.path.join(directory, '__pycache__')
            random_file = os.path.join(cache_directory, 'random-file')
            if HAS_PEP_3147:
                touch(random_file)
            # Cleanup the byte code file.
            cleanup_bytecode_files('bytecode-test', [python_file])
            assert len(bytecode_files) > 0 and all(not os.path.isfile(fn) for fn in bytecode_files), \
                "Failed to cleanup Python byte code file!"
            if HAS_PEP_3147:
                assert os.path.isfile(random_file), \
                    "Byte code cleanup removed unrelated file!"
                os.unlink(random_file)
                cleanup_bytecode_files('test-package', [python_file])
                assert not os.path.isdir(cache_directory), \
                    "Failed to clean up __pycache__ directory!"

    def test_namespace_initialization(self):
        """
        Test namespace package initialization and cleanup.

        This tests the :func:`~py2deb.hooks.initialize_namespaces()` and
        :func:`~py2deb.hooks.cleanup_namespaces()` functions.
        """
        with TemporaryDirectory() as directory:
            package_name = 'namespace-package-test'
            initialize_namespaces(package_name, directory, TEST_NAMESPACES)
            self.check_test_namespaces(directory)
            # Increase the reference count of the top level name space.
            initialize_namespaces(package_name, directory, set([('foo',)]))
            self.check_test_namespaces(directory)
            # Clean up the nested name spaces.
            cleanup_namespaces(package_name, directory, TEST_NAMESPACES)
            # Make sure top level name space is still intact.
            assert os.path.isdir(os.path.join(directory, 'foo'))
            assert os.path.isfile(os.path.join(directory, 'foo', '__init__.py'))
            # Make sure the nested name spaces were cleaned up.
            assert not os.path.isdir(os.path.join(directory, 'foo', 'bar'))
            assert not os.path.isfile(os.path.join(directory, 'foo', 'bar', '__init__.py'))
            assert not os.path.isdir(os.path.join(directory, 'foo', 'bar', 'baz'))
            assert not os.path.isfile(os.path.join(directory, 'foo', 'bar', 'baz', '__init__.py'))
            # Clean up the top level name space as well.
            cleanup_namespaces(package_name, directory, TEST_NAMESPACES)
            assert not os.path.isdir(os.path.join(directory, 'foo'))

    def test_post_install_hook(self):
        """Test the :func:`~py2deb.hooks.post_installation_hook()` function."""
        with TemporaryDirectory() as directory:
            self.run_post_install_hook(directory)
            self.check_test_namespaces(directory)

    def test_pre_removal_hook(self):
        """Test the :func:`~py2deb.hooks.pre_removal_hook()` function."""
        with TemporaryDirectory() as directory:
            self.run_post_install_hook(directory)
            pre_removal_hook(package_name='prerm-test-package',
                             alternatives=set(),
                             modules_directory=directory,
                             namespaces=TEST_NAMESPACES)
            assert not os.path.isdir(os.path.join(directory, 'foo'))

    def run_post_install_hook(self, directory):
        """Helper for :func:`test_post_install_hook()` and :func:`test_pre_removal_hook()`."""
        post_installation_hook(package_name='postinst-test-package',
                               alternatives=set(),
                               modules_directory=directory,
                               namespaces=TEST_NAMESPACES)

    def check_test_namespaces(self, directory):
        """Make sure the test name spaces are properly initialized."""
        assert os.path.isdir(os.path.join(directory, 'foo'))
        assert os.path.isfile(os.path.join(directory, 'foo', '__init__.py'))
        assert os.path.isdir(os.path.join(directory, 'foo', 'bar'))
        assert os.path.isfile(os.path.join(directory, 'foo', 'bar', '__init__.py'))
        assert os.path.isdir(os.path.join(directory, 'foo', 'bar', 'baz'))
        assert os.path.isfile(os.path.join(directory, 'foo', 'bar', 'baz', '__init__.py'))


def find_package_archive(available_archives, package_name):
    """
    Find the ``*.deb`` archive of a specific package.

    :param available_packages: The pathnames of the available package archives
                               (a list of strings).
    :param package_name: The name of the package whose archive file we're
                         interested in (a string).
    :returns: The pathname of the package archive (a string).
    :raises: :exc:`exceptions.AssertionError` if zero or more than one
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
    :func:`deb_pkg_tools.package.inspect_package()`.

    :param contents: The dictionary of package archive entries.
    :param pattern: The filename pattern to match (:mod:`fnmatch` syntax).
    :returns: The metadata of the matched file.
    :raises: :exc:`exceptions.AssertionError` if zero or more than one
             archive entry is found.
    """
    matches = []
    for filename, metadata in contents.items():
        if fnmatch.fnmatch(filename, pattern):
            matches.append(metadata)
    assert len(matches) == 1, "Expected to match exactly one archive entry!"
    return matches[0]


def fix_name_prefix(name):
    """Change the name prefix of a Debian package to match the current Python version."""
    tokens = name.split('-')
    tokens[0] = default_name_prefix()
    return '-'.join(tokens)


def python_callback_fn(converter, package, build_directory):
    """Simple Python function to test support for callbacks."""
    if package.python_name.lower() == 'naturalsort':
        control_file = os.path.join(build_directory, 'DEBIAN', 'control')
        patch_control_file(control_file, dict(
            replaces=converter.transform_name('natsort'),
            breaks=converter.transform_name('natsort'),
        ))
