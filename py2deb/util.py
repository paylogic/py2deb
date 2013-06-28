import os
import re
import sys

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

def transform_package_name(name, prefix, sep='-'):
    '''
    Transforms the name of a Python package as found on PyPi into the name that
    we want it to have as a Debian package using a prefix and a seperator.
    '''
    # Make sure it's lower case
    name = name.lower()
    # Make sure that the only non-alphanumeric
    # character is the seperator
    name = re.sub('[^a-z0-9]+', sep, name)
    prefix = re.sub('[^a-z0-9]+', sep, prefix)
    # Make sure the prefix isn't surrounded by the seperator.
    prefix = prefix.strip(sep)
    # Make sure the name isn't surrounded by the seperator.
    name = name.strip(sep)
    # Prevent double words in the prefix
    prefix_pattern = '^%s%s' % (prefix.rpartition(sep)[2], sep)
    name = re.sub(prefix_pattern, '', name)
    return prefix + sep + name

def run(command, wd=None, verbose=False):
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
