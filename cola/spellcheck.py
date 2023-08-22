import codecs
import collections
import os

from . import resources

__copyright__ = """
2012 Peter Norvig (http://norvig.com/spell-correct.html)
2013-2018 David Aguilar <davvid@gmail.com>
"""

ALPHABET = 'abcdefghijklmnopqrstuvwxyz'


def train(features, model):
    for f in features:
        model[f] += 1
    return model


def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits for c in ALPHABET if b]
    inserts = [a + c + b for a, b in splits for c in ALPHABET]
    return set(deletes + transposes + replaces + inserts)


def known_edits2(word, words):
    return {e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in words}


def known(word, words):
    return {w for w in word if w in words}


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


class NorvigSpellCheck:
    def __init__(
        self,
        words='dict/words',
        propernames='dict/propernames',
    ):
        data_dirs = resources.xdg_data_dirs()
        self.dictwords = resources.find_first(words, data_dirs)
        self.propernames = resources.find_first(propernames, data_dirs)
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
        propernames = self.propernames
        cfg_dictionary = self.dictionary

        if words and os.path.exists(words):
            paths.append((words, True))

        if propernames and os.path.exists(propernames):
            paths.append((propernames, False))

        if cfg_dictionary and os.path.exists(cfg_dictionary):
            paths.append((cfg_dictionary, False))

        for path, title in paths:
            try:
                with codecs.open(
                    path, 'r', encoding='utf-8', errors='ignore'
                ) as words_file:
                    for line in words_file:
                        word = line.rstrip()
                        yield word
                        if title:
                            yield word.title()
            except OSError:
                pass
