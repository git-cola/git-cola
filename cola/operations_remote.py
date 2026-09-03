from __future__ import annotations
from typing import TYPE_CHECKING
from typing import Any

from . import core
from .operations import IOperations
from .operations_local import CmdOutputToFile

if TYPE_CHECKING:
    from . import server

ENCODING = 'utf-8'
IS_LOCAL = True


class RemoteOperations(IOperations):
    def __init__(self, socket_client: server.SocketClient):
        from . import server

        server.check_dependencies()
        self.client = server.SyncSocketClient(socket_client)
        self.seq_number = 0

    def _send_op(self, data: dict[str, Any]):
        current_seq = self.seq_number
        self.seq_number += 1

        data['seq'] = current_seq
        received = self.client.send_message_msgpack(data)
        if received.get('seq', -1) != current_seq:
            raise ValueError(
                f'error: seq number mismatch in client response: {received}'
            )

        if received.get('error', False):
            raise ValueError(f"error: {received.get('result')}")
        try:
            return received['result']
        except KeyError:
            raise ValueError(f'error: missing "result" in response: {received}')

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

        if 'stdout' in kwargs and isinstance(kwargs['stdout'], CmdOutputToFile):
            supported_kwargs['stdout'] = {
                'output_to_file': kwargs['stdout'].path,
                'mode': kwargs['stdout'].mode,
            }

        data = {
            'op': 'run_command',
            'args': [cmd],
            'kwargs': supported_kwargs,
        }

        status, out, err = self._send_op(data)

        return status, core.UStr(out, ENCODING), core.UStr(err, ENCODING)

    def start_monitor(self, worktree: str | None, git_dir: str) -> None:
        data = {
            'op': 'start_monitor',
            'args': [],
            'kwargs': {'worktree': worktree, 'git_dir': git_dir},
        }
        return self._send_op(data)

    def refresh_monitor(self) -> None:
        data = {
            'op': 'refresh_monitor',
            'args': [],
            'kwargs': {},
        }
        return self._send_op(data)

    def poll_monitor(self) -> dict:
        data = {
            'op': 'poll_monitor',
            'args': [],
            'kwargs': {},
        }
        return self._send_op(data)

    def stop_monitor(self) -> None:
        data = {
            'op': 'stop_monitor',
            'args': [],
            'kwargs': {},
        }
        return self._send_op(data)

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
