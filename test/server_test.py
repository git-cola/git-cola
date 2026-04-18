import multiprocessing
import os
import time

from cola import operations
from cola import server


class create_test_server:
    def __init__(self):
        app = server.SocketServer()

        self.server_thread = multiprocessing.Process(target=app.run, daemon=True)
        self.server_thread.start()
        time.sleep(0.4)

    def __enter__(self):
        port = int(os.environ.get('GIT-COLA_SERVER_PORT', 49178))
        self.socket = server.SocketClient(ip='127.0.0.1', port=port)
        self.ops_remote = operations.RemoteOperations(self.socket)
        self.ops_local = operations.LocalOperations()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server_thread.terminate()


def test_server_getcwd():
    with create_test_server() as s:
        assert s.ops_local.getcwd() == s.ops_remote.getcwd()


def test_server_isdir():
    with create_test_server() as s:
        assert s.ops_local.isdir('./testdir') == s.ops_remote.isdir('./testdir')


def test_server_realpath():
    with create_test_server() as s:
        assert s.ops_local.realpath('./testdir') == s.ops_remote.realpath('./testdir')


def test_server_exists():
    with create_test_server() as s:
        assert s.ops_local.exists('./testdir') == s.ops_remote.exists('./testdir')


def test_server_abspath():
    with create_test_server() as s:
        assert s.ops_local.abspath('./testdir') == s.ops_remote.abspath('./testdir')


def test_server_unlink():
    with create_test_server() as s:
        with open('./testfile_local', 'w') as f:
            f.write('test.file')
        with open('./testfile_remote', 'w') as f:
            f.write('test.file')

        assert s.ops_local.unlink('./testfile_local') == s.ops_remote.unlink(
            './testfile_remote'
        )


def test_server_remove():
    with create_test_server() as s:
        for i in range(2):
            with open('test.file', 'w') as f:
                f.close()
            if i == 0:
                rez_local = s.ops_local.remove('./test.file')
            else:
                rez_remote = s.ops_remote.remove('./test.file')

        assert rez_local == rez_remote


def test_server_relpath():
    with create_test_server() as s:
        assert s.ops_local.relpath('./testdir') == s.ops_remote.relpath('./testdir')


def test_server_isfile():
    with create_test_server() as s:
        assert s.ops_local.isfile('./testdir') == s.ops_remote.isfile('./testdir')


def test_server_islink():
    with create_test_server() as s:
        assert s.ops_local.islink('./testdir') == s.ops_remote.islink('./testdir')


def test_server_listdir():
    with create_test_server() as s:
        assert s.ops_local.listdir('./') == s.ops_remote.listdir('./')


def test_server_makedirs():
    with create_test_server() as s:
        rez_local = s.ops_local.makedirs('./test_dir')
        if os.path.exists('./test_dir'):
            os.rmdir('./test_dir')

        rez_remote = s.ops_remote.makedirs('./test_dir')
        if os.path.exists('./test_dir'):
            os.rmdir('./test_dir')

        assert rez_local == rez_remote


def test_server_chdir():
    with create_test_server() as s:
        assert s.ops_local.chdir('./') == s.ops_remote.chdir('./')


def test_server_expanduser():
    with create_test_server() as s:
        assert s.ops_local.expanduser('./') == s.ops_remote.expanduser('./')


def test_server_find_executable():
    with create_test_server() as s:
        assert s.ops_local.find_executable('git', '/') == s.ops_remote.find_executable(
            'git', '/'
        )


def test_server_write_file():
    with create_test_server() as s:
        rez_local = s.ops_local.write_file('./test.file', 'weee')
        if os.path.exists('./test.file'):
            os.remove('./test.file')

        rez_remote = s.ops_remote.write_file('./test.file', 'weee')
        if os.path.exists('./test.file'):
            os.remove('./test.file')

        assert rez_local == rez_remote


def test_server_guess_mimetype():
    with create_test_server() as s:
        assert s.ops_local.guess_mimetype('test.file') == s.ops_remote.guess_mimetype(
            'test.file'
        )


def test_server_rename():
    with create_test_server() as s:
        with open('test.file', 'w') as f:
            f.close()
        rez_local = s.ops_local.rename('test.file', 'test2')
        if os.path.exists('test2'):
            os.remove('test2')

        with open('test.file', 'w') as f:
            f.close()
        rez_remote = s.ops_remote.rename('test.file', 'test2')
        if os.path.exists('test2'):
            os.remove('test2')

        assert rez_local == rez_remote


def test_server_fsync():
    with create_test_server() as s:
        assert s.ops_local.fsync(1) == s.ops_remote.fsync(1)


def test_server_node():
    with create_test_server() as s:
        assert s.ops_local.node() == s.ops_remote.node()


def test_server_print_stderr():
    with create_test_server() as s:
        assert s.ops_local.print_stderr('test.file') == s.ops_remote.print_stderr(
            'test.file'
        )


def test_server_print_stdout():
    with create_test_server() as s:
        assert s.ops_local.print_stdout('test.file') == s.ops_remote.print_stdout(
            'test.file'
        )


def test_server_file_write():
    with create_test_server() as s:
        with open('test.file', 'w') as f:
            f.close()
        assert s.ops_local.file_write(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        ) == s.ops_remote.file_write(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        )
        if os.path.exists('test.file'):
            os.remove('test.file')


def test_server_file_read():
    with create_test_server() as s:
        with open('test.file', 'w') as f:
            f.close()
        assert s.ops_local.file_read('test.file') == s.ops_remote.file_read('test.file')
        if os.path.exists('test.file'):
            os.remove('test.file')


def test_server_file_append():
    with create_test_server() as s:
        with open('test.file', 'w') as f:
            f.close()
        assert s.ops_local.file_append(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        ) == s.ops_remote.file_append(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        )
        if os.path.exists('test.file'):
            os.remove('test.file')


def test_server_list2cmdline():
    with create_test_server() as s:
        assert s.ops_local.list2cmdline('test.file') == s.ops_remote.list2cmdline(
            'test.file'
        )


def test_server_xopen():
    with open('test.file', 'w') as f:
        f.write('Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞\n')
        f.write('2\n')
        f.write('3')

    with create_test_server() as s:
        results_local = []
        with s.ops_local.xopen('test.file') as f:
            for line in f:
                results_local.append(line)

        results_remote = []
        with s.ops_remote.xopen('test.file') as f:
            for line in f:
                results_remote.append(line)

        assert results_local == results_remote

    os.remove('test.file')


def test_server_run_command():
    with create_test_server() as s:
        assert s.ops_local.run_command(
            ['echo', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞']
        ) == s.ops_remote.run_command(['echo', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'])


def test_server_get_environ():
    with create_test_server() as s:
        s.ops_local.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')
        s.ops_remote.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')

        assert (
            s.ops_local.get_environ()['key_test']
            == s.ops_remote.get_environ()['key_test']
        )


def test_server_environ_setdefault():
    with create_test_server() as s:
        assert s.ops_local.environ_setdefault(
            'key_test', 'test_value_世界_🌍_Café_Привет'
        ) == s.ops_remote.environ_setdefault('key_test', 'test_value_世界_🌍_Café_Привет')


def test_server_environ_setvalue():
    with create_test_server() as s:
        s.ops_local.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')
        s.ops_remote.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')

        assert (
            s.ops_local.get_environ()['key_test']
            == s.ops_remote.get_environ()['key_test']
        )


def test_server_environ_pop():
    with create_test_server() as s:
        s.ops_local.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')
        s.ops_remote.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')

        assert s.ops_local.environ_pop('key_test', 'none') == s.ops_remote.environ_pop(
            'key_test', 'none'
        )


def test_server_putenv():
    with create_test_server() as s:
        s.ops_local.putenv('key_test', 'test_value_世界_🌍_Café_Привет')
        s.ops_remote.putenv('key_test', 'test_value_世界_🌍_Café_Привет')

        assert s.ops_local.getenv('key_test') == s.ops_remote.getenv('key_test')


def test_server_unsetenv():
    with create_test_server() as s:
        s.ops_local.putenv('key_test', 'test_value_世界_🌍_Café_Привет')
        s.ops_remote.putenv('key_test', 'test_value_世界_🌍_Café_Привет')

        s.ops_local.unsetenv('key_test')
        s.ops_remote.unsetenv('key_test')

        assert (s.ops_local.getenv('key_test') is None) == (
            s.ops_remote.getenv('key_test') is None
        )
