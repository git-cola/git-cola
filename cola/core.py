"""This module provides unicode encode and decode utilities.
"""
# Some files are not in UTF-8; some other aren't in any codification.
# Remember that GIT doesn't care about encodings (saves binary data)
_encoding_tests = [
        "utf8",
        "iso-8859-15",
        "windows1252",
        "ascii",
        # <-- add encodings here
]
def decode(enc):
    """decode(encoded_string) returns an unencoded unicode string
    """
    for encoding in _encoding_tests:
        try:
            return unicode(enc.decode(encoding))
        except:
            pass
    raise Exception('error encoding %s' % enc)

def encode(unenc):
    """encode(unencoded_string) returns a string encoded in utf-8
    """
    return unenc.encode('utf-8', 'replace')
