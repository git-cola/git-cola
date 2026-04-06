from __future__ import annotations
import os
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Any

from . import core
from . import server
from . import utils

if TYPE_CHECKING:
    from io import BufferedWriter
    from os import stat_result


IS_LOCAL = True


class IOperations(ABC):
    @abstractmethod
    def is_remote(self) -> bool:
        pass

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
    def xwrite(self, fh: BufferedWriter, content: str, encoding: None = None) -> int:
        """Write to a file handle and retry when interrupted"""
        pass

    @abstractmethod
    def wait(self, proc) -> Any:
        """Wait on a subprocess and retry when interrupted"""
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
    def stat(self, path: str) -> stat_result:
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
    def fork(self, args: list[str], cwd: str | None = None, shell: bool = False) -> int:
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

    def xwrite(self, fh: BufferedWriter, content: str, encoding: None = None) -> int:
        """Write to a file handle and retry when interrupted"""
        return core.xwrite(fh, content, encoding)

    def wait(self, proc) -> Any:
        return core.wait(proc)

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

    def stat(self, path: str) -> stat_result:
        return core.stat(path)

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

    def fork(self, args: list[str], cwd: str | None = None, shell: bool = False) -> int:
        return core.fork(args, cwd, shell, self)

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
    def is_remote(self) -> bool:
        return True

    def list2cmdline(self, cmd: list[str | Any | core.UStr]) -> str:
        raise NotImplementedError('Not implemented')

    def xopen(self, path: str, mode: str = 'r', encoding: str | None = None) -> Any:
        raise NotImplementedError('Not implemented')

    def file_append(self, path, text: str, encoding: str | None = None) -> None:
        """Open a file for appending in UTF-8 text mode"""
        raise NotImplementedError('Not implemented')

    def file_read(self, path, encoding: str | None = None) -> str:
        raise NotImplementedError('Not implemented')

    def file_write(self, path: str, text: str, encoding: str | None = None) -> None:
        raise NotImplementedError('Not implemented')

    def print_stdout(self, msg, linesep: str = '\n') -> None:
        raise NotImplementedError('Not implemented')

    def print_stderr(self, msg, linesep: str = '\n') -> None:
        raise NotImplementedError('Not implemented')

    def error(self, msg, status, linesep: str = '\n') -> None:
        raise NotImplementedError('Not implemented')

    def node(
        self,
    ) -> str:
        raise NotImplementedError('Not implemented')

    def fsync(self, fd) -> None:
        raise NotImplementedError('Not implemented')

    def rename(self, old: str, new: str) -> None:
        raise NotImplementedError('Not implemented')

    def guess_mimetype(self, filename: str) -> str | None:
        raise NotImplementedError('Not implemented')

    def getenv(self, name: str, default: str | None = None) -> core.UStr | None:
        raise NotImplementedError('Not implemented')

    def write_file(
        self,
        path: str,
        contents: str,
        encoding: str | None = None,
        append: bool = False,
    ) -> int:
        raise NotImplementedError('Not implemented')

    def xwrite(self, fh: BufferedWriter, content: str, encoding: None = None) -> int:
        """Write to a file handle and retry when interrupted"""
        raise NotImplementedError('Not implemented')

    def wait(self, proc) -> Any:
        raise NotImplementedError('Not implemented')

    def find_executable(
        self, executable: core.UStr | str, path: str | None = None
    ) -> str | None:
        raise NotImplementedError('Not implemented')

    def getcwd(
        self,
    ) -> str:
        raise NotImplementedError('Not implemented')

    def isdir(self, s: str) -> bool:
        raise NotImplementedError('Not implemented')

    def realpath(self, s: str) -> str:
        raise NotImplementedError('Not implemented')

    def exists(self, path: str) -> bool:
        raise NotImplementedError('Not implemented')

    def abspath(self, s: core.UStr | str) -> str:
        raise NotImplementedError('Not implemented')

    def unlink(self, s: str) -> None:
        raise NotImplementedError('Not implemented')

    def stat(self, path: str) -> stat_result:
        raise NotImplementedError('Not implemented')

    def remove(self, path: str) -> None:
        raise NotImplementedError('Not implemented')

    def relpath(self, path: str) -> str | bytes:
        raise NotImplementedError('Not implemented')

    def isfile(self, path: str) -> bool:
        raise NotImplementedError('Not implemented')

    def islink(self, path: str) -> bool:
        raise NotImplementedError('Not implemented')

    def listdir(self, path: Any) -> list[str | bytes]:
        raise NotImplementedError('Not implemented')

    def makedirs(self, name: str) -> None:
        raise NotImplementedError('Not implemented')

    def chdir(self, path: str) -> None:
        raise NotImplementedError('Not implemented')

    def expanduser(self, path: str) -> str:
        raise NotImplementedError('Not implemented')

    def fork(self, args: list[str], cwd: str | None = None, shell: bool = False) -> int:
        raise NotImplementedError('Not implemented')

    def run_command(
        self, cmd: list[core.UStr | str], *args, **kwargs
    ) -> tuple[int, core.UStr, core.UStr]:
        raise NotImplementedError('Not implemented')

    def get_environ(
        self,
    ) -> dict[str, str]:
        raise NotImplementedError('Not implemented')

    def environ_setdefault(self, key: str, value: str) -> str:
        raise NotImplementedError('Not implemented')

    def environ_pop(self, key: str, default: str) -> str | None:
        raise NotImplementedError('Not implemented')

    def environ_setvalue(self, key: str, value: str) -> None:
        raise NotImplementedError('Not implemented')

    def putenv(self, name: str | bytes, value: str | bytes) -> None:
        raise NotImplementedError('Not implemented')

    def unsetenv(self, name: str) -> None:
        raise NotImplementedError('Not implemented')
