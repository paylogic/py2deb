import os
import re
import sys
import urllib
import urlparse

download_cache = os.path.expanduser('~/.pip/download-cache')
source_index = os.path.expanduser('~/.pl-pip/sources')

def get_source_dists(pip_arguments, max_retries=10):
    """
    Download and unpack the source distributions for all dependencies specified
    in the pip command line arguments.
    """
    for directory in [download_cache, source_index]:
        if not os.path.isdir(directory):
            os.makedirs(directory)
    i = 1
    while i < max_retries:
        status, dependencies = unpack_source_dists(pip_arguments)
        if status:
            return dependencies
        download_source_dists(pip_arguments)
        i += 1
    raise Exception, "pip failed %i times!" % max_retries

def unpack_source_dists(pip_arguments):
    """
    Run pip to check whether we have local source distributions available for
    all dependencies. We parse the output of pip to find the names and versions
    of the packages selected by pip.
    """
    # Create a shallow copy of the original argument
    # list that includes the --no-install option.
    modified_arguments = [a for a in pip_arguments]
    modified_arguments.extend(['-v', '-v', '--no-install'])

    # Execute pip to unpack the source distributions.
    status, output = run_pip(modified_arguments,
                             local_index=source_index,
                             use_remote_index=False)

    # If pip failed, we should retry.
    if not status:
        return False, None

    # If pip succeeded, parse its output to find the pinned dependencies.
    dependencies = []
    pattern = re.compile(r'^\s*Source in (.+?) has version (.+?), which satisfies requirement')
    for line in output:
        m = pattern.match(line)
        if m:
            directory = os.path.abspath(m.group(1))
            name = os.path.basename(directory)
            version = m.group(2)
            dependencies.append((name, version, directory))
    return True, dependencies

def download_source_dists(pip_arguments):
    """
    Download missing source distributions.
    """
    # Create a shallow copy of the original argument
    # list that includes the --no-install option.
    modified_arguments = [a for a in pip_arguments]
    modified_arguments.append('--no-install')

    # Execute pip to download missing source distributions.
    run_pip(modified_arguments,
            local_index=source_index,
            use_remote_index=True)

def run_pip(arguments, local_index, use_remote_index):
    """
    Execute a modified `pip install` command.
    """
    command_line = []
    for i, arg in enumerate(arguments):
        if arg == 'install':
            command_line += ['pip'] + arguments[:i+1] + [
                    '--download-cache=%s' % download_cache,
                    '--find-links=file://%s' % local_index]
            if not use_remote_index:
                command_line += ['--no-index']
            command_line += arguments[i+1:]
            break
    else:
        command_line += ['pip'] + arguments
    print "Running pip!", ' '.join(command_line)
    pip = os.popen('bash -c "%s"' % ' '.join(command_line))
    output = []
    for line in pip:
        sys.stderr.write("%s\n" % line.rstrip())
        output.append(line)
    if pip.close() is None:
        update_source_dists_index()
        return True, output
    else:
        return False, None

def update_source_dists_index():
    """
    Link newly downloaded source distributions into the local index directory.
    """
    for download_name in os.listdir(download_cache):
        download_path = os.path.join(download_cache, download_name)
        url = urllib.unquote(download_name)
        if not url.endswith('.content-type'):
            components = urlparse.urlparse(url)
            archive_name = os.path.basename(components.path)
            archive_path = os.path.join(source_index, add_extension(download_path, archive_name))
            if not os.path.isfile(archive_path):
                os.symlink(download_path, archive_path)

def add_extension(download_path, archive_path):
    """
    Make sure all cached source distributions have the right file extension.
    """
    handle = os.popen('file "%s"' % os.path.realpath(download_path))
    output = handle.read()
    if 'gzip' in output:
        if not archive_path.endswith(('.tgz', '.tar.gz')):
            archive_path += '.tar.gz'
    elif 'bzip2' in output:
        if not archive_path.endswith('.bz2'):
            archive_path += '.bz2'
    elif 'zip' in output:
        if not archive_path.endswith('.zip'):
            archive_path += '.zip'
    return archive_path

# vim: ft=python ts=4 sw=4
