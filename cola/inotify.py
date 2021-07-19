from __future__ import absolute_import, division, print_function, unicode_literals
import ctypes
import ctypes.util
import errno
import os

# constant from Linux include/uapi/linux/limits.h
NAME_MAX = 255

# constants from Linux include/uapi/linux/inotify.h
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200

IN_Q_OVERFLOW = 0x00004000

IN_ONLYDIR = 0x01000000
IN_EXCL_UNLINK = 0x04000000
IN_ISDIR = 0x80000000


class inotify_event(ctypes.Structure):
    _fields_ = [
        ('wd', ctypes.c_int),
        ('mask', ctypes.c_uint32),
        ('cookie', ctypes.c_uint32),
        ('len', ctypes.c_uint32),
    ]


MAX_EVENT_SIZE = ctypes.sizeof(inotify_event) + NAME_MAX + 1


def _errcheck(result, func, arguments):
    if result >= 0:
        return result
    err = ctypes.get_errno()
    if err == errno.EINTR:
        return func(*arguments)
    raise OSError(err, os.strerror(err))


try:
    _libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
    _read = _libc.read
    init = _libc.inotify_init
    add_watch = _libc.inotify_add_watch
    rm_watch = _libc.inotify_rm_watch
except AttributeError:
    raise ImportError('Could not load inotify functions from libc')


_read.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t]
_read.errcheck = _errcheck

init.argtypes = []
init.errcheck = _errcheck

add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
add_watch.errcheck = _errcheck

rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
rm_watch.errcheck = _errcheck


def read_events(inotify_fd, count=64):
    buf = ctypes.create_string_buffer(MAX_EVENT_SIZE * count)
    n = _read(inotify_fd, buf, ctypes.sizeof(buf))

    addr = ctypes.addressof(buf)
    while n:
        assert n >= ctypes.sizeof(inotify_event)
        event = inotify_event.from_address(addr)
        addr += ctypes.sizeof(inotify_event)
        n -= ctypes.sizeof(inotify_event)
        if event.len:
            assert n >= event.len
            name = ctypes.string_at(addr)
            addr += event.len
            n -= event.len
        else:
            name = None
        yield event.wd, event.mask, event.cookie, name
