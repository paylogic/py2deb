# py2deb: Python to Debian package converter.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: August 5, 2020
# URL: https://py2deb.readthedocs.io

"""
Python package namespace auto detection.

This module is used by :pypi:`py2deb` to detect pkgutil-style `namespace
packages`_ to enable special handling of the ``__init__.py`` files involved,
because these would otherwise cause :man:`dpkg` file conflicts.

.. note:: The ``__init__.py`` files that define pkgutil-style namespace
          packages can contain arbitrary Python code (including comments and
          with room for minor differences in coding style) which makes reliable
          identification harder than it should be. We use :func:`ast.parse()`
          to look for hints and only when we find enough hints do we consider a
          module to be part of a pkgutil-style namespace package.

.. _namespace packages: https://packaging.python.org/guides/packaging-namespace-packages/
"""

# Standard library modules.
import ast
import logging
import os

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

# Public identifiers that require documentation.
__all__ = ("find_pkgutil_namespaces", "find_pkgutil_ns_hints", "find_python_modules")


def find_pkgutil_namespaces(directory):
    """
    Find the `pkgutil-style namespace packages`_ in an unpacked Python distribution archive.

    :param directory:

      The pathname of a directory containing an unpacked Python distribution
      archive (a string).

    :returns:

      A generator of dictionaries similar to those returned by
      :func:`find_python_modules()`.

    This function combines :func:`find_python_modules()` and
    :func:`find_pkgutil_ns_hints()` to make it easy for callers
    to identify the namespace packages defined by an unpacked
    Python distribution archive.
    """
    for details in find_python_modules(directory):
        logger.debug("Checking file for pkgutil-style namespace definition: %s", details['abspath'])
        try:
            with open(details['abspath']) as handle:
                contents = handle.read()
            # The intention of the following test is to start with a cheap test
            # to quickly disqualify large and irrelevant __init__.py files,
            # without having to parse their full AST.
            if "pkgutil" in contents:
                module = ast.parse(contents, filename=details['abspath'])
                hints = find_pkgutil_ns_hints(module)
                if len(hints) >= 5:
                    yield details
        except Exception:
            logger.warning("Swallowing exception during pkgutil-style namespace analysis ..", exc_info=True)


def find_pkgutil_ns_hints(tree):
    """
    Analyze an AST for hints that we're dealing with a Python module that defines a pkgutil-style namespace package.

    :param tree:

      The result of :func:`ast.parse()` when run on a Python module (which is
      assumed to be an ``__init__.py`` file).

    :returns:

      A :class:`set` of strings where each string represents a hint (an
      indication) that we're dealing with a pkgutil-style namespace module. No
      single hint can definitely tell us, but a couple of unique hints taken
      together should provide a reasonable amount of confidence (at least this
      is the idea, how well this works in practice remains to be seen).
    """
    hints = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr == "extend_path":
                logger.debug("Found hint! ('extend_path' reference)")
                hints.add("extend_path")
        elif isinstance(node, ast.Import) and any(alias.name == "pkgutil" for alias in node.names):
            logger.debug("Found hint! (import pkg_util)")
            hints.update(("import", "pkgutil"))
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module == "pkgutil"
            and any(alias.name == "extend_path" for alias in node.names)
        ):
            logger.debug("Found hint! (from pkg_util import extend_path)")
            hints.update(("import", "pkgutil", "extend_path"))
        elif isinstance(node, ast.Name):
            if node.id == "extend_path":
                logger.debug("Found hint! ('extend_path' reference)")
                hints.add("extend_path")
            elif node.id == "pkgutil":
                logger.debug("Found hint! ('pkgutil' reference)")
                hints.add("pkgutil")
            elif node.id == "__import__":
                logger.debug("Found hint! ('__import__' reference)")
                hints.add("import")
            elif node.id == "__name__":
                logger.debug("Found hint! ('__name__' reference)")
                hints.add("__name__")
            elif node.id == "__path__":
                logger.debug("Found hint! ('__path__' reference)")
                hints.add("__path__")
        elif isinstance(node, ast.Str) and node.s in ("pkgutil", "extend_path"):
            logger.debug("Found hint! ('%s' string literal)", node.s)
            hints.add(node.s)
    return hints


def find_python_modules(directory):
    """
    Find the Python modules in an unpacked Python distribution archive.

    :param directory:

      The pathname of a directory containing an unpacked Python distribution
      archive (a string).

    :returns: A list of dictionaries with the following key/value pairs:

              - ``abspath`` gives the absolute pathname of a Python module (a string).
              - ``relpath`` gives the pathname of a Python module (a string)
                relative to the intended installation directory.
              - ``name`` gives the dotted name of a Python module (a string).

    This function works as follows:

    1. Use :func:`os.walk()` to recursively search for ``__init__.py`` files in
       the directory given by the caller and collect the relative pathnames of
       the directories containing the ``__init__.py`` files.

    2. Use :func:`os.path.commonprefix()` to determine the common prefix of the
       resulting directory pathnames.

    3. Use :func:`os.path.split()` to partition the common prefix into an
       insignificant part (all but the final pathname component) and the
       significant part (the final pathname component).

    4. Strip the insignificant part of the common prefix from the directory
       pathnames we collected in step 1.

    5. Replace :data:`os.sep` occurrences with dots to convert (what remains
       of) the directory pathnames to "dotted paths".
    """
    logger.debug("Searching for pkgutil-style namespace packages in %s ..", directory)
    # Find the relative pathnames of all __init__.py files (relative
    # to the root directory given to us by the caller).
    modules = []
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename == "__init__.py":
                abspath = os.path.join(root, filename)
                relpath = os.path.relpath(abspath, directory)
                # Ignore a top level "build" directory (generated by pip).
                path_segments = relpath.split(os.path.sep)
                if not (path_segments and path_segments[0] == 'build'):
                    module_path, basename = os.path.split(relpath)
                    modules.append({
                        'abspath': abspath,
                        'relpath': relpath,
                        'name': module_path,
                    })
    logger.debug("Found modules defined using __init__.py files: %s", modules)
    # Determine the common prefix of the module paths.
    common_prefix = os.path.commonprefix([m['name'] for m in modules])
    logger.debug("Determined common prefix: %s", common_prefix)
    # Separate the path segments at the start of the common prefix (which are
    # insignificant for our purposes) from the final path segment (which is
    # essential for our purposes).
    head, tail = os.path.split(common_prefix)
    if head and tail:
        logger.debug("Stripping insignificant part of prefix: [%s/]%s", head, tail)
    else:
        logger.debug("Common prefix has no insignificant part (nothing to strip).")
    # Prepare to strip the insignificant part of the common prefix (the
    # +1 is to strip the dot that leads up to the final path segment).
    strip_length = len(head) + 1 if head else 0
    # Translate (what remains of) the module pathnames to dotted names.
    for details in modules:
        if strip_length > 0:
            # Strip the insignificant part of the common prefix.
            details['name'] = details['name'][strip_length:]
            details['relpath'] = details['relpath'][strip_length:]
        # Translate pathnames to dotted names.
        details['name'] = details['name'].replace(os.sep, ".")
        # Share our results with the caller.
        yield details
