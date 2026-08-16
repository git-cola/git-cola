import multiprocessing
import os
import time

from cola import operations
from cola import server


class create_test_server:
    def __init__(self):
        app = server.SocketServer('127.0.0.1', 49178, True)

        self.server_thread = multiprocessing.Process(target=app.run, daemon=True)
        self.server_thread.start()
        time.sleep(0.4)

    def __enter__(self):
        port = int(os.environ.get('GIT_COLA_TEST_SERVER_PORT', 49178))
        self.socket = server.SocketClient(ip='127.0.0.1', port=port)
        self.ops_remote = operations.RemoteOperations(self.socket)
        self.ops_local = operations.LocalOperations()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server_thread.terminate()


def test_server_getcwd():
    with create_test_server() as service:
        assert service.ops_local.getcwd() == service.ops_remote.getcwd()


def test_server_isdir():
    with create_test_server() as service:
        assert service.ops_local.isdir('test/tmp/testdir') == service.ops_remote.isdir(
            'test/tmp/testdir'
        )


def test_server_realpath():
    with create_test_server() as service:
        assert service.ops_local.realpath(
            'test/tmp/testdir'
        ) == service.ops_remote.realpath('test/tmp/testdir')


def test_server_exists():
    with create_test_server() as service:
        assert service.ops_local.exists(
            'test/tmp/testdir'
        ) == service.ops_remote.exists('test/tmp/testdir')


def test_server_abspath():
    with create_test_server() as service:
        assert service.ops_local.abspath(
            'test/tmp/testdir'
        ) == service.ops_remote.abspath('test/tmp/testdir')


def test_server_unlink():
    with create_test_server() as service:
        with open('./testfile_local', 'w') as fh:
            fh.write('test.file')
        with open('./testfile_remote', 'w') as fh:
            fh.write('test.file')

        assert service.ops_local.unlink(
            './testfile_local'
        ) == service.ops_remote.unlink('./testfile_remote')


def test_server_remove():
    with create_test_server() as service:
        for i in range(2):
            with open('test.file', 'w') as fh:
                fh.close()
            if i == 0:
                rez_local = service.ops_local.remove('./test.file')
            else:
                rez_remote = service.ops_remote.remove('./test.file')
        assert rez_local == rez_remote


def test_server_relpath():
    with create_test_server() as service:
        assert service.ops_local.relpath(
            'test/tmp/testdir'
        ) == service.ops_remote.relpath('test/tmp/testdir')


def test_server_isfile():
    with create_test_server() as service:
        assert service.ops_local.isfile(
            'test/tmp/testdir'
        ) == service.ops_remote.isfile('test/tmp/testdir')


def test_server_islink():
    with create_test_server() as service:
        assert service.ops_local.islink(
            'test/tmp/testdir'
        ) == service.ops_remote.islink('test/tmp/testdir')


def test_server_listdir():
    with create_test_server() as service:
        assert service.ops_local.listdir('./') == service.ops_remote.listdir('./')


def test_server_makedirs():
    with create_test_server() as service:
        rez_local = service.ops_local.makedirs('test/tmp/test_dir')
        if os.path.exists('test/tmp/test_dir'):
            os.rmdir('test/tmp/test_dir')

        rez_remote = service.ops_remote.makedirs('test/tmp/test_dir')
        if os.path.exists('test/tmp/test_dir'):
            os.rmdir('test/tmp/test_dir')

        assert rez_local == rez_remote


def test_server_chdir():
    with create_test_server() as service:
        assert service.ops_local.chdir('./') == service.ops_remote.chdir('./')


def test_server_expanduser():
    with create_test_server() as service:
        assert service.ops_local.expanduser('./') == service.ops_remote.expanduser('./')


def test_server_find_executable():
    with create_test_server() as service:
        assert service.ops_local.find_executable(
            'git', '/'
        ) == service.ops_remote.find_executable('git', '/')


def test_server_write_file():
    with create_test_server() as service:
        rez_local = service.ops_local.write_file('./test.file', 'weee')
        if os.path.exists('./test.file'):
            os.remove('./test.file')

        rez_remote = service.ops_remote.write_file('./test.file', 'weee')
        if os.path.exists('./test.file'):
            os.remove('./test.file')

        assert rez_local == rez_remote


def test_server_guess_mimetype():
    with create_test_server() as service:
        assert service.ops_local.guess_mimetype(
            'test.file'
        ) == service.ops_remote.guess_mimetype('test.file')


def test_server_rename():
    with create_test_server() as service:
        with open('test.file', 'w') as f:
            f.close()
        rez_local = service.ops_local.rename('test.file', 'test2')
        if os.path.exists('test2'):
            os.remove('test2')

        with open('test.file', 'w') as f:
            f.close()
        rez_remote = service.ops_remote.rename('test.file', 'test2')
        if os.path.exists('test2'):
            os.remove('test2')

        assert rez_local == rez_remote


def test_server_fsync():
    with create_test_server() as service:
        assert service.ops_local.fsync(1) == service.ops_remote.fsync(1)


def test_server_node():
    with create_test_server() as service:
        assert service.ops_local.node() == service.ops_remote.node()


def test_server_print_stderr():
    with create_test_server() as service:
        assert service.ops_local.print_stderr(
            'test.file'
        ) == service.ops_remote.print_stderr('test.file')


def test_server_print_stdout():
    with create_test_server() as service:
        assert service.ops_local.print_stdout(
            'test.file'
        ) == service.ops_remote.print_stdout('test.file')


def test_server_file_write():
    with create_test_server() as service:
        with open('test.file', 'w') as f:
            f.close()
        assert service.ops_local.file_write(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        ) == service.ops_remote.file_write(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        )
        if os.path.exists('test.file'):
            os.remove('test.file')


def test_server_file_read():
    with create_test_server() as service:
        with open('test.file', 'w') as f:
            f.close()
        assert service.ops_local.file_read('test.file') == service.ops_remote.file_read(
            'test.file'
        )
        if os.path.exists('test.file'):
            os.remove('test.file')


def test_server_file_append():
    with create_test_server() as service:
        with open('test.file', 'w') as f:
            f.close()
        assert service.ops_local.file_append(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        ) == service.ops_remote.file_append(
            'test.file', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞'
        )
        if os.path.exists('test.file'):
            os.remove('test.file')


def test_server_list2cmdline():
    with create_test_server() as service:
        assert service.ops_local.list2cmdline(
            'test.file'
        ) == service.ops_remote.list2cmdline('test.file')


def test_server_xopen():
    with open('test.file', 'w') as f:
        f.write('Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞\n')
        f.write('2\n')
        f.write('3')

    with create_test_server() as service:
        results_local = []
        with service.ops_local.xopen('test.file') as f:
            for line in f:
                results_local.append(line)

        results_remote = []
        with service.ops_remote.xopen('test.file') as f:
            for line in f:
                results_remote.append(line)

        assert results_local == results_remote

    os.remove('test.file')


def test_server_run_command():
    with create_test_server() as service:
        assert service.ops_local.run_command(
            ['echo', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞']
        ) == service.ops_remote.run_command(
            ['echo', 'Hello, 世界! 👋 Привет, мир! 🌍 Café ☕ ∑∞']
        )


def test_server_get_environ():
    with create_test_server() as service:
        service.ops_local.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')
        service.ops_remote.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')

        assert (
            service.ops_local.get_environ()['key_test']
            == service.ops_remote.get_environ()['key_test']
        )


def test_server_environ_setdefault():
    with create_test_server() as service:
        assert service.ops_local.environ_setdefault(
            'key_test', 'test_value_世界_🌍_Café_Привет'
        ) == service.ops_remote.environ_setdefault(
            'key_test', 'test_value_世界_🌍_Café_Привет'
        )


def test_server_environ_setvalue():
    with create_test_server() as service:
        service.ops_local.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')
        service.ops_remote.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')

        assert (
            service.ops_local.get_environ()['key_test']
            == service.ops_remote.get_environ()['key_test']
        )


def test_server_environ_pop():
    with create_test_server() as service:
        service.ops_local.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')
        service.ops_remote.environ_setvalue('key_test', 'test_value_世界_🌍_Café_Привет')

        assert service.ops_local.environ_pop(
            'key_test', 'none'
        ) == service.ops_remote.environ_pop('key_test', 'none')


def test_server_putenv():
    with create_test_server() as service:
        service.ops_local.putenv('key_test', 'test_value_世界_🌍_Café_Привет')
        service.ops_remote.putenv('key_test', 'test_value_世界_🌍_Café_Привет')

        assert service.ops_local.getenv('key_test') == service.ops_remote.getenv(
            'key_test'
        )


def test_server_unsetenv():
    with create_test_server() as service:
        service.ops_local.putenv('key_test', 'test_value_世界_🌍_Café_Привет')
        service.ops_remote.putenv('key_test', 'test_value_世界_🌍_Café_Привет')

        service.ops_local.unsetenv('key_test')
        service.ops_remote.unsetenv('key_test')

        assert (service.ops_local.getenv('key_test') is None) == (
            service.ops_remote.getenv('key_test') is None
        )
