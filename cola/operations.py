from __future__ import annotations
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

from . import core

ENCODING = 'utf-8'
IS_LOCAL = True


@dataclass
class CmdOutputToFile:
    path: str
    mode: str


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

    @abstractmethod
    def start_monitor(self, worktree: str | None, git_dir: str) -> None:
        pass

    @abstractmethod
    def refresh_monitor(self) -> None:
        pass

    @abstractmethod
    def poll_monitor(self) -> dict:
        pass

    @abstractmethod
    def stop_monitor(self) -> None:
        pass
