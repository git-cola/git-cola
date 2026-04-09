""" """
from __future__ import annotations
import asyncio
import sys
import threading
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
    if msgpack is None:
        print('msgpack package was not found')
        sys.exit(1)

    if websockets is None:
        print('websockets package was not found')
        sys.exit(1)


class SocketServer:
    def __init__(self, port: int = 49178):
        check_dependencies()
        self.port = port
        self.ops = operations.LocalOperations()

    async def message_handler(self, websocket):
        async for message_bytes in websocket:
            message = msgpack.unpackb(message_bytes)
            try:
                print(f'Received: {message}')

                func_dict = self.ops.function_dict()

                if message.get('op') in func_dict:
                    method = func_dict.get(message.get('op'))
                    args = message.get('args', [])
                    kwargs = message.get('kwargs', {})

                    result = method(self.ops, *args, **kwargs)

                    await websocket.send(
                        msgpack.packb({
                            'seq_number': message.get('seq_number'),
                            'op': 'response',
                            'result': result,
                        })
                    )
                else:
                    await websocket.send(
                        msgpack.packb({
                            'seq_number': message.get('seq_number'),
                            'op': 'response',
                            'result': 'Unknown command',
                            'is_exception': True,
                        })
                    )

            except Exception as e:
                import traceback

                await websocket.send(
                    msgpack.packb({
                        'seq_number': message.get('seq_number'),
                        'op': 'response',
                        'result': str(e),
                        'is_exception': True,
                        'traceback': traceback.format_exc(),
                    })
                )

    async def run_async(self):
        async with websockets.serve(
            self.message_handler, '0.0.0.0', self.port, max_size=10 * 1024 * 1024
        ):
            print(f'Server running on ws://0.0.0.0:{self.port}')
            await asyncio.Future()  # run forever

    def run(self):
        asyncio.run(self.run_async())


class SocketClient:
    def __init__(self, ip: str, port: int = 49178, protocol: str = 'ws'):
        check_dependencies()
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
            print(f'Connection failure! {err}')
            sys.exit(1)

    async def send_message_msgpack(self, message: dict[str, Any]) -> Any:
        packed_message = msgpack.packb(message)
        return await self.send_message(
            packed_message,
            message.get('seq_number'),
        )

    async def send_message(self, message: str, seq_number: int):
        if self.websocket is None:
            raise RuntimeError('WebSocket is not connected')

        await self.websocket.send(message)
        async with self._recv_lock:
            result = msgpack.unpackb(await self.websocket.recv())
            while result.get('seq_number') != seq_number:
                result = msgpack.unpackb(await self.websocket.recv())
            return result


class SyncSocketClient:
    def __init__(self, async_client: SocketClient):
        check_dependencies()
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


def run() -> None:
    """Start the websocket server."""
    SocketServer().run()


if __name__ == '__main__':
    run()
