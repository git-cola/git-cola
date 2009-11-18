import os

import cola
from cola import qtutils
from cola import signals


def clone_repo(parent, spawn=True):
    """
    Present GUI controls for cloning a repository

    A new cola session is invoked when 'spawn' is True.

    """
    url, ok = qtutils.prompt('Path or URL to clone (Env. $VARS okay)')
    url = os.path.expandvars(url)
    if not ok or not url:
        return None
    try:
        # Pick a suitable basename by parsing the URL
        newurl = url.replace('\\', '/')
        default = newurl.rsplit('/', 1)[-1]
        if default == '.git':
            # The end of the URL is /.git, so assume it's a file path
            default = os.path.basename(os.path.dirname(newurl))
        if default.endswith('.git'):
            # The URL points to a bare repo
            default = default[:-4]
        if url == '.':
            # The URL is the current repo
            default = os.path.basename(os.getcwd())
        if not default:
            raise
    except:
        cola.notifier().broadcast(signals.information,
                                  'Error Cloning',
                                  'Could not parse: "%s"' % url)
        qtutils.log(1, 'Oops, could not parse git url: "%s"' % url)
        return None

    # Prompt the user for a directory to use as the parent directory
    msg = 'Select a parent directory for the new clone'
    dirname = qtutils.opendir_dialog(parent, msg, cola.model().getcwd())
    if not dirname:
        return None
    count = 1
    destdir = os.path.join(dirname, default)
    olddestdir = destdir
    if os.path.exists(destdir):
        # An existing path can be specified
        msg = ('"%s" already exists, cola will create a new directory' %
               destdir)
        cola.notifier().broadcast(signals.information,
                                  'Directory Exists', msg)

    # Make sure the new destdir doesn't exist
    while os.path.exists(destdir):
        destdir = olddestdir + str(count)
        count += 1
    cola.notifier().broadcast(signals.clone, url, destdir,
                              spawn=spawn)
    return destdir
