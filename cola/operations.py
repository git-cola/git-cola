from __future__ import annotations
import io
import os
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from . import core
from . import utils

if TYPE_CHECKING:
    from . import server

ENCODING = 'utf-8'
IS_LOCAL = True


class IOperations(ABC):
    @abstractmethod
    def is_remote(self) -> bool:
        pass

    @classmethod
    def function_dict(cls):
        return {
            name: val
            for name, val in cls.__dict__.items()
            if callable(val) and not name.startswith('__')
        }

    @abstractmethod
    def list2cmdline(self, cmd: list[str | Any | core.UStr]) -> str:
        pass

    @abstractmethod
    def xopen(self, path: str, mode: str = 'r', encoding: str | None = None) -> Any:
        pass

    @abstractmethod
    def file_append(self, path, text: str, encoding: str | None = None) -> None:
        """Open a file for appending in UTF-8 text mode"""
        pass

    @abstractmethod
    def file_read(self, path, encoding: str | None = None) -> str:
        pass

    @abstractmethod
    def file_write(self, path: str, text: str, encoding: str | None = None) -> None:
        pass

    @abstractmethod
    def print_stdout(self, msg, linesep: str = '\n') -> None:
        pass

    @abstractmethod
    def print_stderr(self, msg, linesep: str = '\n') -> None:
        pass

    @abstractmethod
    def error(self, msg, status, linesep: str = '\n') -> None:
        pass

    @abstractmethod
    def node(
        self,
    ) -> str:
        pass

    @abstractmethod
    def fsync(self, fd: int) -> None:
        pass

    @abstractmethod
    def rename(self, old: str, new: str) -> None:
        pass

    @abstractmethod
    def guess_mimetype(self, filename: str) -> str | None:
        pass

    @abstractmethod
    def getenv(self, name: str, default=None) -> core.UStr | None:
        pass

    @abstractmethod
    def write_file(
        self,
        path: str,
        contents: str,
        encoding: str | None = None,
        append: bool = False,
    ) -> int:
        """Writes a Unicode string to a file"""
        pass

    @abstractmethod
    def find_executable(
        self, executable: core.UStr | str, path: str | None = None
    ) -> str | None:
        pass

    @abstractmethod
    def getcwd(
        self,
    ) -> str:
        pass

    @abstractmethod
    def isdir(self, s: str) -> bool:
        pass

    @abstractmethod
    def realpath(self, s: str) -> str:
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        pass

    @abstractmethod
    def abspath(self, s: core.UStr | str) -> str:
        pass

    @abstractmethod
    def unlink(self, s: str) -> None:
        pass

    @abstractmethod
    def stat(self, path: str) -> dict[str, int]:
        pass

    @abstractmethod
    def remove(self, path: str) -> None:
        pass

    @abstractmethod
    def relpath(self, path: str) -> str | bytes:
        pass

    @abstractmethod
    def isfile(self, path: str) -> bool:
        pass

    @abstractmethod
    def islink(self, path: str) -> bool:
        pass

    @abstractmethod
    def listdir(self, path: Any) -> list[Any]:
        pass

    @abstractmethod
    def makedirs(self, name: str) -> None:
        pass

    @abstractmethod
    def chdir(self, path: str) -> None:
        pass

    @abstractmethod
    def expanduser(self, path: str) -> str:
        pass

    @abstractmethod
    def run_command(
        self, cmd: list[core.UStr | str], *args, **kwargs
    ) -> tuple[int, core.UStr, core.UStr]:
        pass

    @abstractmethod
    def get_environ(
        self,
    ) -> dict[str, str]:
        pass

    @abstractmethod
    def environ_setdefault(self, key: str, value: str) -> str:
        pass

    @abstractmethod
    def environ_pop(self, key: str, default: str) -> str | None:
        pass

    @abstractmethod
    def environ_setvalue(self, key: str, value: str) -> None:
        pass

    @abstractmethod
    def putenv(self, name: str | bytes, value: str | bytes) -> None:
        pass

    @abstractmethod
    def unsetenv(self, name: str) -> None:
        pass

    @abstractmethod
    def tmp_filename(self, label: str, suffix: str = '') -> str:
        pass


class LocalOperations(IOperations):
    def is_remote(self) -> bool:
        return False

    def list2cmdline(self, cmd: list[str | Any | core.UStr]) -> str:
        return core.list2cmdline(cmd)

    def xopen(self, path: str, mode: str = 'r', encoding: str | None = None) -> Any:
        return core.xopen(path, mode, encoding)

    def file_append(self, path, text: str, encoding: str | None = None) -> None:
        with core.open_append(path, encoding) as file:
            file.write(text)

    def file_read(self, path, encoding: str | None = None) -> str:
        with core.open_read(path, encoding) as file:
            return file.read()

    def file_write(self, path: str, text: str, encoding: str | None = None) -> None:
        with core.open_write(path, encoding) as file:
            file.write(text)

    def print_stdout(self, msg, linesep: str = '\n') -> None:
        return core.print_stdout(msg, linesep)

    def print_stderr(self, msg, linesep: str = '\n') -> None:
        return core.print_stderr(msg, linesep)

    def error(self, msg, status, linesep: str = '\n') -> None:
        return core.error(msg, status, linesep)

    def node(
        self,
    ) -> str:
        return core.node()

    def fsync(self, fd: int) -> None:
        return core.fsync(fd)

    def rename(self, old: str, new: str) -> None:
        return core.rename(old, new)

    def guess_mimetype(self, filename: str) -> str | None:
        return core.guess_mimetype(filename)

    def getenv(self, name: str, default: str | None = None) -> core.UStr | None:
        if default:
            return core.getenv(name, default)
        return core.getenv(name)

    def write_file(
        self,
        path: str,
        contents: str,
        encoding: str | None = None,
        append: bool = False,
    ) -> int:
        """Writes a Unicode string to a file"""
        return core.write(path, contents, encoding, append)

    def find_executable(
        self, executable: core.UStr | str, path: str | None = None
    ) -> str | None:
        return core.find_executable(executable, path)

    def getcwd(
        self,
    ) -> str:
        return core.getcwd()

    def isdir(self, s: str) -> bool:
        return core.isdir(s)

    def realpath(self, s: str) -> str:
        return core.realpath(s)

    def exists(self, path: str) -> bool:
        return core.exists(path)

    def abspath(self, s: core.UStr | str) -> str:
        return core.abspath(s)

    def unlink(self, s: str) -> None:
        return core.unlink(s)

    def stat(self, path: str) -> dict[str, int]:
        st = core.stat(path)

        return {'st_mtime': st.st_mtime}

    def remove(self, path: str) -> None:
        return core.remove(path)

    def relpath(self, path: str) -> str | bytes:
        return core.relpath(path)

    def isfile(self, path: str) -> bool:
        return core.isfile(path)

    def islink(self, path: str) -> bool:
        return core.islink(path)

    def listdir(self, path: Any) -> list[str | bytes]:
        return core.listdir(path)

    def makedirs(self, name: str) -> None:
        return core.makedirs(name)

    def chdir(self, path: str) -> None:
        return core.chdir(path)

    def expanduser(self, path: str) -> str:
        return core.expanduser(path)

    def run_command(
        self, cmd: list[core.UStr | str], *args, **kwargs
    ) -> tuple[int, core.UStr, core.UStr]:
        return core.run_command(cmd, *args, **kwargs)

    def get_environ(
        self,
    ) -> dict[str, str]:
        return dict(os.environ)

    def environ_setdefault(self, key: str, value: str) -> str:
        return os.environ.setdefault(key, value)

    def environ_pop(self, key: str, default: str) -> str | None:
        return os.environ.pop(key, None)

    def environ_setvalue(self, key: str, value: str) -> None:
        os.environ[key] = value

    def putenv(self, name: str | bytes, value: str | bytes) -> None:
        return os.putenv(name, value)

    def unsetenv(self, name: str) -> None:
        return os.unsetenv(name)

    def tmp_filename(self, label: str, suffix: str = '') -> str:
        return utils.tmp_filename(label, suffix)


class RemoteOperations(IOperations):
    def __init__(self, socket_client: server.SocketClient):
        from . import server

        self.client = server.SyncSocketClient(socket_client)
        self.seq_number = 0

    def _send_op(self, data: dict[str, Any]):
        data['seq_number'] = self.seq_number
        received = self.client.send_message_msgpack(data)
        if received.get('seq_number') != data.get('seq_number'):
            raise OSError('seq_number was not correct')
        self.seq_number += 1

        if received.get('is_exception', False):
            raise OSError(f"Error was found: {received.get('result')}")

        if 'error' in received:
            raise RuntimeError(received['error'])

        return received.get('result')

    def is_remote(self) -> bool:
        return True

    def list2cmdline(self, cmd: list[str | Any | core.UStr]) -> str:
        data = {
            'op': 'list2cmdline',
            'args': [],
            'kwargs': {
                'cmd': cmd,
            },
        }
        return self._send_op(data)

    def xopen(self, path: str, mode: str = 'r', encoding: str | None = None) -> Any:
        """Open a file for appending in UTF-8 text mode"""
        data = {
            'op': 'file_read',
            'args': [],
            'kwargs': {
                'path': path,
                'encoding': encoding,
            },
        }
        if mode == 'rb':
            return io.BytesIO(self._send_op(data))

        return io.StringIO(self._send_op(data))

    def file_append(self, path, text: str, encoding: str | None = None) -> None:
        """Open a file for appending in UTF-8 text mode"""
        data = {
            'op': 'file_append',
            'args': [],
            'kwargs': {
                'path': path,
                'text': text,
                'encoding': encoding,
            },
        }
        return self._send_op(data)

    def file_read(self, path, encoding: str | None = None) -> str:
        data = {
            'op': 'file_read',
            'args': [],
            'kwargs': {
                'path': path,
                'encoding': encoding,
            },
        }
        return self._send_op(data)

    def file_write(self, path: str, text: str, encoding: str | None = None) -> None:
        data = {
            'op': 'file_write',
            'args': [],
            'kwargs': {
                'path': path,
                'text': text,
                'encoding': encoding,
            },
        }
        return self._send_op(data)

    def print_stdout(self, msg, linesep: str = '\n') -> None:
        data = {
            'op': 'print_stdout',
            'args': [],
            'kwargs': {
                'msg': msg,
                'linesep': linesep,
            },
        }
        return self._send_op(data)

    def print_stderr(self, msg, linesep: str = '\n') -> None:
        data = {
            'op': 'print_stderr',
            'args': [],
            'kwargs': {
                'msg': msg,
                'linesep': linesep,
            },
        }
        return self._send_op(data)

    def error(self, msg, status, linesep: str = '\n') -> None:
        data = {
            'op': 'error',
            'args': [],
            'kwargs': {
                'msg': msg,
                'status': status,
                'linesep': linesep,
            },
        }
        return self._send_op(data)

    def node(
        self,
    ) -> str:
        data = {
            'op': 'node',
            'args': [],
            'kwargs': {},
        }
        return self._send_op(data)

    def fsync(self, fd) -> None:
        data = {
            'op': 'fsync',
            'args': [],
            'kwargs': {
                'fd': fd,
            },
        }
        return self._send_op(data)

    def rename(self, old: str, new: str) -> None:
        data = {
            'op': 'rename',
            'args': [],
            'kwargs': {
                'old': old,
                'new': new,
            },
        }
        return self._send_op(data)

    def guess_mimetype(self, filename: str) -> str | None:
        data = {
            'op': 'guess_mimetype',
            'args': [],
            'kwargs': {
                'filename': filename,
            },
        }
        return self._send_op(data)

    def getenv(self, name: str, default: str | None = None) -> core.UStr | None:
        data = {
            'op': 'getenv',
            'args': [],
            'kwargs': {
                'name': name,
                'default': default,
            },
        }
        return self._send_op(data)

    def write_file(
        self,
        path: str,
        contents: str,
        encoding: str | None = None,
        append: bool = False,
    ) -> int:
        data = {
            'op': 'write_file',
            'args': [],
            'kwargs': {
                'path': path,
                'contents': contents,
                'encoding': encoding,
                'append': append,
            },
        }
        return self._send_op(data)

    def find_executable(
        self, executable: core.UStr | str, path: str | None = None
    ) -> str | None:
        data = {
            'op': 'find_executable',
            'args': [],
            'kwargs': {'executable': executable, 'path': path},
        }
        return self._send_op(data)

    def getcwd(
        self,
    ) -> str:
        data = {
            'op': 'getcwd',
            'args': [],
            'kwargs': {},
        }
        return self._send_op(data)

    def isdir(self, s: str) -> bool:
        data = {
            'op': 'isdir',
            'args': [],
            'kwargs': {'s': s},
        }
        return self._send_op(data)

    def realpath(self, s: str) -> str:
        data = {
            'op': 'realpath',
            'args': [],
            'kwargs': {'s': s},
        }
        return self._send_op(data)

    def exists(self, path: str) -> bool:
        data = {
            'op': 'exists',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def abspath(self, s: core.UStr | str) -> str:
        data = {
            'op': 'abspath',
            'args': [],
            'kwargs': {'s': s},
        }
        return self._send_op(data)

    def unlink(self, s: str) -> None:
        data = {
            'op': 'unlink',
            'args': [],
            'kwargs': {'s': s},
        }
        return self._send_op(data)

    def stat(self, path: str) -> dict[str, int]:
        def validate_path(path: str):
            if not path:
                raise ValueError('Empty path')

            if '\t' in path or '\n' in path:
                path = path.replace('b\t', '')
                if '\t' in path or '\n' in path:
                    raise ValueError(f'Invalid control chars in path: {repr(path)}')

                return path

            if path.startswith('b"') or path.startswith("b'"):
                raise ValueError(f'Looks like raw bytes: {repr(path)}')

            return path

        data = {
            'op': 'stat',
            'args': [],
            'kwargs': {'path': validate_path(path)},
        }
        return self._send_op(data)

    def remove(self, path: str) -> None:
        data = {
            'op': 'remove',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def relpath(self, path: str) -> str | bytes:
        data = {
            'op': 'relpath',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def isfile(self, path: str) -> bool:
        data = {
            'op': 'isfile',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def islink(self, path: str) -> bool:
        data = {
            'op': 'islink',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def listdir(self, path: Any) -> list[str | bytes]:
        data = {
            'op': 'listdir',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def makedirs(self, name: str) -> None:
        data = {
            'op': 'makedirs',
            'args': [],
            'kwargs': {'name': name},
        }
        return self._send_op(data)

    def chdir(self, path: str) -> None:
        data = {
            'op': 'chdir',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def expanduser(self, path: str) -> str:
        data = {
            'op': 'expanduser',
            'args': [],
            'kwargs': {'path': path},
        }
        return self._send_op(data)

    def run_command(self, cmd, *args, **kwargs):
        supported_kwargs = {}

        # Filter keyword arguments to those supported by the msgpack.
        # This avoids serialization failures caused by non-serializable
        # Python objects, such as builtin functions passed via preexec_fn.
        if 'cwd' in kwargs and isinstance(kwargs['cwd'], str):
            supported_kwargs['cwd'] = kwargs['cwd']

        if 'env' in kwargs and isinstance(kwargs['env'], dict):
            supported_kwargs['env'] = dict(kwargs['env'])

        data = {
            'op': 'run_command',
            'args': [cmd],
            'kwargs': supported_kwargs,
        }

        status, out, err = self._send_op(data)

        return status, core.UStr(out, ENCODING), core.UStr(err, ENCODING)

    def get_environ(
        self,
    ) -> dict[str, str]:
        data = {
            'op': 'get_environ',
            'args': [],
            'kwargs': {},
        }
        return self._send_op(data)

    def environ_setdefault(self, key: str, value: str) -> str:
        data = {
            'op': 'environ_setdefault',
            'args': [],
            'kwargs': {'key': key, 'value': value},
        }
        return self._send_op(data)

    def environ_pop(self, key: str, default: str) -> str | None:
        data = {
            'op': 'environ_pop',
            'args': [],
            'kwargs': {'key': key, 'default': default},
        }
        return self._send_op(data)

    def environ_setvalue(self, key: str, value: str) -> None:
        data = {
            'op': 'environ_setvalue',
            'args': [],
            'kwargs': {'key': key, 'value': value},
        }
        return self._send_op(data)

    def putenv(self, name: str | bytes, value: str | bytes) -> None:
        data = {
            'op': 'putenv',
            'args': [],
            'kwargs': {'name': name, 'value': value},
        }
        return self._send_op(data)

    def unsetenv(self, name: str) -> None:
        data = {
            'op': 'unsetenv',
            'args': [],
            'kwargs': {'name': name},
        }
        return self._send_op(data)

    def tmp_filename(self, label: str, suffix: str = '') -> str:
        data = {
            'op': 'tmp_filename',
            'args': [],
            'kwargs': {'label': label, 'suffix': suffix},
        }
        return self._send_op(data)
