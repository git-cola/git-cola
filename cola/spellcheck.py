from __future__ import absolute_import, division, print_function, unicode_literals
import collections
import os

from cola import core

__copyright__ = """
2012 Peter Norvig (http://norvig.com/spell-correct.html)
2013-2018 David Aguilar <davvid@gmail.com>
"""

alphabet = 'abcdefghijklmnopqrstuvwxyz'


def train(features, model):
    for f in features:
        model[f] += 1
    return model


def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits for c in alphabet if b]
    inserts = [a + c + b for a, b in splits for c in alphabet]
    return set(deletes + transposes + replaces + inserts)


def known_edits2(word, words):
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in words)


def known(word, words):
    return set(w for w in word if w in words)


def suggest(word, words):
    candidates = (
        known([word], words)
        or known(edits1(word), words)
        or known_edits2(word, words)
        or [word]
    )
    return candidates


def correct(word, words):
    candidates = suggest(word, words)
    return max(candidates, key=words.get)


class NorvigSpellCheck(object):
    def __init__(
        self,
        words='/usr/share/dict/words',
        cracklib='/usr/share/dict/cracklib-small',
        propernames='/usr/share/dict/propernames',
    ):
        self.dictwords = words
        self.cracklib = cracklib
        self.propernames = propernames
        self.words = collections.defaultdict(lambda: 1)
        self.extra_words = set()
        self.dictionary = None
        self.initialized = False

    def set_dictionary(self, dictionary):
        self.dictionary = dictionary

    def init(self):
        if self.initialized:
            return
        self.initialized = True
        train(self.read(), self.words)
        train(self.extra_words, self.words)

    def add_word(self, word):
        self.extra_words.add(word)

    def suggest(self, word):
        self.init()
        return suggest(word, self.words)

    def check(self, word):
        self.init()
        return word.replace('.', '') in self.words

    def read(self):
        """Read dictionary words"""
        paths = []

        words = self.dictwords
        cracklib = self.cracklib
        propernames = self.propernames
        cfg_dictionary = self.dictionary

        if cracklib and os.path.exists(cracklib):
            paths.append((cracklib, True))
        elif words and os.path.exists(words):
            paths.append((words, True))

        if propernames and os.path.exists(propernames):
            paths.append((propernames, False))

        if cfg_dictionary and os.path.exists(cfg_dictionary):
            paths.append((cfg_dictionary, False))

        for (path, title) in paths:
            try:
                with open(path, 'r') as f:
                    for word in f:
                        word = core.decode(word.rstrip())
                        yield word
                        if title:
                            yield word.title()
            except IOError:
                pass
