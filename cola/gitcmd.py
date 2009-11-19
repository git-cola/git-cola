import os

from cola import git


# Provides access to a global GitCola instance
_instance = None
def instance():
    """Return the GitCola singleton"""
    global _instance
    if _instance:
        return _instance
    _instance = GitCola()
    return _instance


class GitCola(git.Git):
    """
    Subclass git.Git to provide custom behaviors.

    GitPython throws exceptions by default.
    We suppress exceptions in favor of return values.

    """
    def __init__(self):
        git.Git.__init__(self)
        self.load_worktree(os.getcwd())

    def load_worktree(self, path):
        self._git_dir = path
        self._worktree = None
        self.worktree()

    def worktree(self):
        if self._worktree:
            return self._worktree
        self.git_dir()
        if self._git_dir:
            curdir = self._git_dir
        else:
            curdir = os.getcwd()

        if self._is_git_dir(os.path.join(curdir, '.git')):
            return curdir

        # Handle bare repositories
        if (len(os.path.basename(curdir)) > 4
                and curdir.endswith('.git')):
            return curdir
        if 'GIT_WORK_TREE' in os.environ:
            self._worktree = os.getenv('GIT_WORK_TREE')
        if not self._worktree or not os.path.isdir(self._worktree):
            if self._git_dir:
                gitparent = os.path.join(os.path.abspath(self._git_dir), '..')
                self._worktree = os.path.abspath(gitparent)
                self.set_cwd(self._worktree)
        return self._worktree

    def is_valid(self):
        return self._git_dir and self._is_git_dir(self._git_dir)

    def git_dir(self):
        if self.is_valid():
            return self._git_dir
        if 'GIT_DIR' in os.environ:
            self._git_dir = os.getenv('GIT_DIR')
        if self._git_dir:
            curpath = os.path.abspath(self._git_dir)
        else:
            curpath = os.path.abspath(os.getcwd())
        # Search for a .git directory
        while curpath:
            if self._is_git_dir(curpath):
                self._git_dir = curpath
                break
            gitpath = os.path.join(curpath, '.git')
            if self._is_git_dir(gitpath):
                self._git_dir = gitpath
                break
            curpath, dummy = os.path.split(curpath)
            if not dummy:
                break
        return self._git_dir

    def _is_git_dir(self, d):
        """From git's setup.c:is_git_directory()."""
        if (os.path.isdir(d)
                and os.path.isdir(os.path.join(d, 'objects'))
                and os.path.isdir(os.path.join(d, 'refs'))):
            headref = os.path.join(d, 'HEAD')
            return (os.path.isfile(headref)
                    or (os.path.islink(headref)
                    and os.readlink(headref).startswith('refs')))
        return False
