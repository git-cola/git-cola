import os

def fixture(*paths):
    return os.path.join(os.path.dirname(__file__), 'fixtures', *paths)
