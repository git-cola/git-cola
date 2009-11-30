from cola import gitcmd

git = gitcmd.instance()


def commits(max_count=200):
    log = git.log(all=True,
                  topo_order=True,
                  # put subject at the end b/c it can contain
                  # any number of funky characters
                  pretty='format:%h}:{%p}:{%d}:{%an}:{%aD}:{%s',
                  max_count=max_count)
    return [Commit(log_entry=line) for line in log.splitlines()]


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
        self.sha1, parents, tags, author, authdate, subject = \
                log_entry.split('}:{', 5)
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
                self.tags.add(tag)
        if author:
            self.author = author
        if authdate:
            self.authdate = authdate

        return self

    def __repr__(self):
        return ("{\n"
                "  sha1: " + self.sha1 + "\n"
                "  subject: " + self.subject + "\n"
                "  author: " + self.author + "\n"
                "  authdate: " + self.authdate + "\n"
                "  parents: [" + ', '.join(self.parents) + "]\n"
                "  tags: [" + ', '.join(self.tags) + "]\n"
                "}")
