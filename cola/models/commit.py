from cola import gitcmd
from cola import gitcmds
from cola import utils

# put subject at the end b/c it can contain
# any number of funky characters
logfmt = 'format:%H%x00%P%x00%d%x00%an%x00%aD%x00%s'
git = gitcmd.instance()




class Commit(object):
    __slots__ = ('sha1', 'subject', 'parents', 'tags', 'author', 'authdate')
    def __init__(self, sha1='', log_entry=''):
        self.sha1 = sha1
        self.subject = ''
        self.parents = []
        self.tags = set()
        self.author = ''
        self.authdate = ''
        if log_entry:
            self.parse(log_entry)

    def parse(self, log_entry):
        self.sha1 = log_entry[:40]
        (parents, tags, author, authdate, subject) = \
                log_entry[41:].split('\0', 5)

        if subject:
            self.subject = subject
        if parents:
            for parent in parents.split(' '):
                self.parents.append(parent)
        if tags:
            for tag in tags[2:-1].split(', '):
                if tag.startswith('tag: '):
                    tag = tag[5:] # tag: refs/
                elif tag.startswith('refs/remotes/'):
                    tag = tag[13:] # refs/remotes/
                elif tag.startswith('refs/heads/'):
                    tag = tag[11:] # refs/heads/
                if tag.endswith('/HEAD'):
                    continue
                self.tags.add(tag)
        if author:
            self.author = author
        if authdate:
            self.authdate = authdate

        return self

    def __str__(self):
        return self.sha1

    def __repr__(self):
        return ("{\n"
                "  sha1: " + self.sha1 + "\n"
                "  subject: " + self.subject + "\n"
                "  author: " + self.author + "\n"
                "  authdate: " + self.authdate + "\n"
                "  parents: [" + ', '.join(self.parents) + "]\n"
                "  tags: [" + ', '.join(self.tags) + "]\n"
                "}")


class RepoReader(object):
    def __init__(self, args=None):
        if args is None:
            args = ('HEAD',)
        self.git = git
        self._proc = None
        self._objects = {}
        self._cmd = ('git', 'log',
                     '--topo-order',
                     '--pretty='+logfmt) + tuple(args)
        self._cached = False
        """Indicates that all data has been read"""
        self._idx = -1
        """Index into the cached commits"""
        self._topo_list = []
        """List of commits objects in topological order"""

    cached = property(lambda self: self._cached)
    """Return True when no commits remain to be read"""

    def reset(self):
        if self._proc:
            self._topo_list = []
            self._proc.kill()
        self._proc = None

    def __iter__(self):
        if self._cached:
            return self
        self.reset()
        return self

    def next(self):
        if self._cached:
            try:
                self._idx += 1
                return self._topo_list[self._idx]
            except IndexError:
                self._idx = -1
                raise StopIteration
        if self._proc is None:
            self._proc = utils.start_command(self._cmd)
            self._topo_list = []
        log_entry = self._proc.stdout.readline()
        if not log_entry:
            self._proc.kill()
            del self._proc
            self._cached = True
            self._proc = None
            raise StopIteration
        sha1 = log_entry[:40]
        try:
            return self._objects[sha1]
        except KeyError:
            c = Commit(log_entry=log_entry)
            self._objects[c.sha1] = c
            self._topo_list.append(c)
            return c

    def __getitem__(self, sha1):
        return self._objects[sha1]

    def items(self):
        return self._objects.items()
