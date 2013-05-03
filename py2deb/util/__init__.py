import re

def transform_package_name(self, name):
    '''
    Transforms the name of a Python package as found on PyPi into the name that
    we want it to have as a Debian package (using our prefix).
    '''
    name = name.lower()
    name = re.sub('^python-', '', name)
    name = re.sub('[^a-z0-9]+', '-', name)
    name = name.strip('-')
    return 'pl-python-' + name
