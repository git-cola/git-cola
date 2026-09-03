from __future__ import annotations
import os
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from qtpy import QtCore

from . import core
from . import fsmonitor
from . import git
from . import gitcfg
from . import utils
from .operations import IOperations

ENCODING = 'utf-8'
IS_LOCAL = True

if TYPE_CHECKING:
    from .fsmonitor import Monitor


@dataclass
class CmdOutputToFile:
    path: str
    mode: str


class MonitorContext:
    def __init__(self, ops: IOperations) -> None:
        self.ops = ops
        self.git: git.Git = None
        self.cfg: gitcfg.GitConfig = None


class LocalOperations(IOperations):
    def __init__(self) -> None:
        self._monitor: Monitor = None
        self._monitor_lock = threading.Lock()
        self._monitor_state = {'files': False, 'config': False}

    def is_remote(self) -> bool:
        return False

    def list2cmdline(self, cmd: list[str | Any | core.UStr]) -> str:
        return core.list2cmdline(cmd)

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
        self,
        cmd: list[core.UStr | str],
        *args,
        **kwargs,
    ) -> tuple[int, core.UStr, core.UStr]:
        stdout = None

        if (
            isinstance(kwargs.get('stdout'), dict)
            and 'output_to_file' in kwargs['stdout']
        ):
            stdout = CmdOutputToFile(
                kwargs['stdout']['output_to_file'],
                kwargs['stdout'].get('mode', 'wb'),
            )
        else:
            stdout = kwargs.get('stdout')

        if stdout and isinstance(stdout, CmdOutputToFile):
            with core.xopen(stdout.path, stdout.mode) as f:
                kwargs['stdout'] = f
                return core.run_command(cmd, *args, **kwargs)
        else:
            return core.run_command(cmd, *args, **kwargs)

    def start_monitor(self, worktree: str | None, git_dir: str) -> None:
        if self._monitor is not None:
            return

        context = MonitorContext(self)
        context.git = git.create()
        context.git.set_worktree(worktree or git_dir)
        context.cfg = gitcfg.create(context)  # type: ignore[arg-type]

        monitor = fsmonitor.create(context)  # type: ignore[arg-type]

        def mark(kind: str):
            def handler() -> None:
                with self._monitor_lock:
                    self._monitor_state[kind] = True

            return handler

        monitor.files_changed.connect(mark('files'), QtCore.Qt.DirectConnection)
        monitor.config_changed.connect(mark('config'), QtCore.Qt.DirectConnection)
        monitor.start()
        self._monitor = monitor

    def refresh_monitor(self) -> None:
        if self._monitor is not None:
            self._monitor.refresh()

    def poll_monitor(self) -> dict:
        with self._monitor_lock:
            state = dict(self._monitor_state)
            self._monitor_state = {'files': False, 'config': False}
        return state

    def stop_monitor(self) -> None:
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor = None

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
