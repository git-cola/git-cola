def encode(string):
    try:
        result = string.encode('utf-8')
    except (ValueError, UnicodeEncodeError):
        result = string
    return result


def make_string(x):
    if x:
        x = str(x)
    return x


def stringify_options(items):
    return [[make_string(x) for x in i] for i in items]


def stringify_list(items):
    return [make_string(i) for i in items]
