"""Display models and utility functions"""
from __future__ import absolute_import, division, print_function, unicode_literals
import collections


def shorten_paths(source_paths):
    """Shorten a sequence of paths into unique strings for display"""
    result = {}
    # Start by assuming that all paths are in conflict.
    # On each iteration we will collect all the path suffixes, move the newly
    # unique entries to the result, and repeat until no conflicts remain.
    count = 0
    conflicts = list(source_paths)
    in_conflict = True
    while in_conflict:
        count += 1
        # Gather the suffixes for the current paths in conflict
        suffixes = collections.defaultdict(list)
        for path in conflicts:
            suffix = path_suffix(path, count)
            suffixes[suffix].append(path)

        # Loop over the suffixes to gather new conflicts and unique entries.
        conflicts = []
        in_conflict = False

        for suffix, paths in suffixes.items():
            # If only a single path exists for the suffix then no conflict
            # exists, and the suffix is valid.
            if len(paths) == 1:
                result[paths[0]] = suffix
            # If this loop runs too long then bail out by using the full path.
            elif count >= 128:
                for path in paths:
                    result[path] = path
            # If multiple paths map to the same suffix then the paths are
            # considered in conflict, and will be reprocessed.
            else:
                conflicts.extend(paths)
                in_conflict = True

    return result


def path_suffix(path, count):
    """Return `count` number of trailing path components"""
    path = normalize_path(path)
    components = path.split('/')[-count:]
    return '/'.join(components)


def normalize_path(path):
    """Normalize a path so that only "/" is used as a separator"""
    return path.replace('\\', '/')
