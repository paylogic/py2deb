import re

def compact(text, **kw):
    """
    Trim and compact whitespace and .format() the resulting string.
    """
    return ' '.join(text.split()).format(**kw)

def transform_package_name(name):
    '''
    Transforms the name of a Python package as found on PyPi into the name that
    we want it to have as a Debian package (using our prefix).
    '''
    name = name.lower()
    name = re.sub('^python-', '', name)
    name = re.sub('[^a-z0-9]+', '-', name)
    name = name.strip('-')
    return 'pl-python-' + name
