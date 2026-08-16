"""Server and client code for remote execution of cola operations"""
from __future__ import annotations
import asyncio
import datetime
import os
import socket
import sys
import textwrap
import threading
import traceback
from typing import Any

try:
    import msgpack
except ImportError:
    msgpack = None

try:
    import websockets
except ImportError:
    websockets = None

from . import operations


def check_dependencies() -> None:
    errors = []
    if msgpack is None:
        errors.append('error: missing package: msgpack (python3-msgpack)')
    if websockets is None:
        errors.append('error: missing package: websockets (python3-websockets)')
    if errors:
        sys.exit('\n'.join(errors))


class SocketServer:
    def __init__(self, address: str, port: int, verbose: bool):
        self.address = address
        self.port = port
        self.verbose = verbose
        self.ops = operations.LocalOperations()

    async def message_handler(self, websocket):
        try:
            async for message_bytes in websocket:
                await self._process_message(websocket, message_bytes)
        except websockets.exceptions.ConnectionClosedError:
            log('client disconnected')

    async def _process_message(self, websocket, message_bytes):
        message = msgpack.unpackb(message_bytes)
        if self.verbose:
            log(f'message: {message}')

        func_dict = self.ops.function_dict()
        try:
            op_name = message['op']
            seq = message['seq']
        except KeyError:
            await websocket.send(
                msgpack.packb({
                    'seq': message.get('seq', -1),
                    'op': 'response',
                    'result': f'invalid message: "op" and "seq" are required: {message}',
                    'error': True,
                })
            )
            return

        try:
            method = func_dict[op_name]
        except KeyError:
            await websocket.send(
                msgpack.packb({
                    'seq': seq,
                    'op': 'response',
                    'result': f'unknown command: {op_name}',
                    'error': True,
                })
            )
            return

        args = message.get('args', [])
        kwargs = message.get('kwargs', {})

        try:
            result = method(self.ops, *args, **kwargs)
        except Exception as err:
            await websocket.send(
                msgpack.packb({
                    'seq': seq,
                    'op': 'response',
                    'result': str(err),
                    'error': True,
                    'traceback': traceback.format_exc(),
                })
            )
            return

        await websocket.send(
            msgpack.packb({
                'seq': seq,
                'op': 'response',
                'result': result,
            })
        )

    async def run_async(self):
        async with websockets.serve(
            self.message_handler, self.address, self.port, max_size=10 * 1024 * 1024
        ):
            await asyncio.Future()  # run forever

    def run(self):
        asyncio.run(self.run_async())


class SocketClient:
    def __init__(self, ip: str, port: int = 49178, protocol: str = 'ws'):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.websocket = None
        self._recv_lock = None

    async def connect(self):
        try:
            self._recv_lock = asyncio.Lock()
            self.websocket = await websockets.connect(
                f'{self.protocol}://{self.ip}:{self.port}',
                max_size=10 * 1024 * 1024,
            )
        except Exception as err:
            sys.exit(timestamp(f'error: connection failure: {err}'))

    async def send_message_msgpack(self, message: dict[str, Any]) -> Any:
        packed_message = msgpack.packb(message)
        return await self.send_message(
            packed_message,
            message.get('seq'),
        )

    async def send_message(self, message: str, seq_number: int):
        if self.websocket is None:
            raise RuntimeError('WebSocket is not connected')

        await self.websocket.send(message)
        async with self._recv_lock:
            result = msgpack.unpackb(await self.websocket.recv())
            while result.get('seq', -1) != seq_number:
                result = msgpack.unpackb(await self.websocket.recv())
            return result


class SyncSocketClient:
    def __init__(self, async_client: SocketClient):
        self.client = async_client
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        self._run(self.client.connect())

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()  # blocks until done

    def send_message_msgpack(self, message: dict[str, Any]):
        return self._run(self.client.send_message_msgpack(message))

    def send_message(self, message: str, seq_number: int):
        return self._run(self.client.send_message(message, seq_number))


def run(address, port, verbose) -> None:
    """Start the websocket cola operations server"""
    log(f'cola server running at ws://{address}:{port}')
    server = SocketServer(address, port, verbose)
    try:
        return server.run()
    except KeyboardInterrupt:
        print('\r', end='')
        log('server shutdown')


def stderr(msg):
    print(textwrap.dedent(msg), file=sys.stderr)


def log(msg):
    stderr(timestamp(msg))


def timestamp(msg):
    now = datetime.datetime.now()
    timestamp = now.strftime('%Y-%m-%d %I:%M:%S %p')
    return f'{timestamp}  {msg}'


def warn(msg):
    for line in textwrap.dedent(msg).splitlines():
        stderr('warning: ' + line)


def print_warnings(address, port):
    check_dependencies()

    stderr(
        'cola server is currently experimental and **INSECURE**! USE AT YOUR OWN RISK.'
    )
    if address == '0.0.0.0':
        stderr('')
        warn('Binding to 0.0.0.0 enables unsafe network connections!')
        warn('Use ssh to tunnel the server port over ssh instead.')
        warn(
            """
            ANYONE on your network could potentially issue commands that do irreparable
            damage on the host where the server is running.

            cola server enables REMOTE CODE EXECUTION that can do amazing things.
            It can also potentially cause perform irreparable damage if misued by anyone
            with nothing more than network access to your host.

            Only use cola server in trusted environments you fully control.
            NEVER EXPOSE A COLA SERVER TO THE OPEN INTERNET OR EVEN PUBLIC WIFI.
            IF YOU DO NOT TRUST PEERS ON YOUR NETWORK, DO NOT USE THIS SOFTWARE.
        """
        )

    hostname = socket.gethostname()
    username = os.environ.get('USER', os.getlogin())
    if port != 42069:
        connect_cmd = f'git cola connect localhost:{port}'
    else:
        connect_cmd = 'git cola connect'

    stderr(
        f"""
        To create a secure tunnel from a remote client into the cola server using ssh,
        adjust the server hostname as necessary and run the following on the remote client:

                $ ssh -L {port}:localhost:{port} {username}@{hostname}

        Once the tunnel is running, run this on the remote host to connect to the server:

                $ {connect_cmd}
    """
    )
