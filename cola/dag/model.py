import os
import subprocess

from cola import core
from cola.git import git
from cola import utils
from cola.observable import Observable

# put summary at the end b/c it can contain
# any number of funky characters, including the separator
logfmt = 'format:%H%x01%P%x01%d%x01%an%x01%ad%x01%ae%x01%s'
logsep = chr(0x01)


class CommitFactory(object):
    root_generation = 0
    commits = {}

    @classmethod
    def reset(cls):
        cls.commits.clear()
        cls.root_generation = 0

    @classmethod
    def new(cls, sha1=None, log_entry=None):
        if not sha1 and log_entry:
            sha1 = log_entry[:40]
        try:
            commit = cls.commits[sha1]
            if log_entry and not commit.parsed:
                commit.parse(log_entry)
            cls.root_generation = max(commit.generation,
                                      cls.root_generation)
        except KeyError:
            commit = Commit(sha1=sha1,
                            log_entry=log_entry)
            if not log_entry:
                cls.root_generation += 1
                commit.generation = max(commit.generation,
                                        cls.root_generation)
            cls.commits[sha1] = commit
        return commit


class DAG(Observable):
    ref_updated = 'ref_updated'
    count_updated = 'count_updated'

    def __init__(self, ref, count):
        Observable.__init__(self)
        self.ref = ref
        self.count = count
        self.overrides = {}

    def set_ref(self, ref):
        changed = ref != self.ref
        self.ref = ref
        self.notify_observers(self.ref_updated)
        return changed

    def set_count(self, count):
        changed = count != self.count
        self.count = count
        self.notify_observers(self.count_updated)
        return changed

    def set_options(self, opts, args):
        if opts is not None:
            if self.set_count(opts.count):
                self.overrides['count'] = opts.count

        if args is not None:
            ref = subprocess.list2cmdline([core.decode(a) for a in args])
            if self.set_ref(ref):
                self.overrides['ref'] = ref

    def overridden(self, opt):
        return opt in self.overrides

    def paths(self):
        all_refs = utils.shell_split(self.ref)
        if '--' in all_refs:
            all_refs = all_refs[all_refs.index('--'):]

        return [p for p in all_refs
                    if p and os.path.exists(core.encode(p))]


class Commit(object):
    root_generation = 0

    __slots__ = ('sha1',
                 'summary',
                 'parents',
                 'children',
                 'tags',
                 'author',
                 'authdate',
                 'email',
                 'generation',
                 'parsed')
    def __init__(self, sha1=None, log_entry=None):
        self.sha1 = sha1
        self.summary = None
        self.parents = []
        self.children = []
        self.tags = set()
        self.email = None
        self.author = None
        self.authdate = None
        self.parsed = False
        self.generation = CommitFactory.root_generation
        if log_entry:
            self.parse(log_entry)

    def parse(self, log_entry, sep=logsep):
        self.sha1 = log_entry[:40]
        (parents, tags, author, authdate, email, summary) = \
                log_entry[41:].split(sep, 6)

        if summary:
            self.summary = core.decode(summary)

        if parents:
            generation = None
            for parent_sha1 in parents.split(' '):
                parent = CommitFactory.new(sha1=parent_sha1)
                parent.children.append(self)
                if generation is None:
                    generation = parent.generation+1
                self.parents.append(parent)
                generation = max(parent.generation+1, generation)
            self.generation = generation

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
                self.tags.add(core.decode(tag))
        if author:
            self.author = core.decode(author)
        if authdate:
            self.authdate = authdate
        if email:
            self.email = core.decode(email)

        self.parsed = True
        return self

    def __str__(self):
        return self.sha1

    def __repr__(self):
        return ("{\n"
                "  sha1: " + self.sha1 + "\n"
                "  summary: " + self.summary + "\n"
                "  author: " + self.author + "\n"
                "  authdate: " + self.authdate + "\n"
                "  parents: [" + ', '.join(self.parents) + "]\n"
                "  tags: [" + ', '.join(self.tags) + "]\n"
                "}")


    def is_fork(self):
        ''' Returns True if the node is a fork'''
        return len(self.children) > 1
    
    def is_merge(self):
        ''' Returns True if the node is a fork'''
        return len(self.parents) > 1

class RepoReader(object):
    def __init__(self, dag, git=git):
        self.dag = dag
        self.git = git
        self._proc = None
        self._objects = {}
        self._cmd = ['git', 'log',
                     '--topo-order',
                     '--reverse',
                     '--pretty='+logfmt]
        self._cached = False
        """Indicates that all data has been read"""
        self._idx = -1
        """Index into the cached commits"""
        self._topo_list = []
        """List of commits objects in topological order"""

    cached = property(lambda self: self._cached)
    """Return True when no commits remain to be read"""


    def __len__(self):
        return len(self._topo_list)

    def reset(self):
        CommitFactory.reset()
        if self._proc:
            self._topo_list = []
            self._proc.kill()
        self._proc = None
        self._cached = False

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
            ref_args = utils.shell_split(self.dag.ref)
            cmd = self._cmd + ['-%d' % self.dag.count] + ref_args
            self._proc = utils.start_command(cmd)
            self._topo_list = []

        log_entry = core.readline(self._proc.stdout).rstrip()
        if not log_entry:
            del self._proc
            self._cached = True
            self._proc = None
            raise StopIteration

        sha1 = log_entry[:40]
        try:
            return self._objects[sha1]
        except KeyError:
            c = CommitFactory.new(log_entry=log_entry)
            self._objects[c.sha1] = c
            self._topo_list.append(c)
            return c

    def __getitem__(self, sha1):
        return self._objects[sha1]

    def items(self):
        return self._objects.items()
