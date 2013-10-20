# Custom exceptions raised by py2deb.

class Py2debError(Exception):
    """
    Base exception for all exceptions explicitly raised by py2deb.
    """

class BackendFailed(Py2debError):
    """
    Exception raised by py2deb when the current backend has failed.
    """

# vim: ts=4 sw=4 et
