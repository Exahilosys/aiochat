import asyncio

from . import helpers


__all__ = ('Channel',)


class Types:

    REQUEST = 0
    RESPONSE = 1


class Channel:

    __slots__ = ('_send', '_recv', '_waiters', '_handle', '_loop')

    def __init__(self, send, recv, loop = None):

        if not loop:

            loop = asyncio.get_event_loop()

        self._send = send

        self._recv = recv

        self._handle = None

        self._waiters = {}

        self._loop = loop

    def bind(self, handle):

        self._handle = handle

    def _push(self, type, nonce, data):

        data = (type, nonce, data)

        return self._send(data)

    async def request(self, data):

        type = Types.REQUEST

        nonces = self._waiters.keys()

        nonce = helpers.unique(nonces)

        future = self._loop.create_future()

        self._waiters[nonce] = future

        await self._push(type, nonce, data)

        try:

            data = await future

        except asyncio.CancelledError:

            future.cancel()

            del self._waiters[nonce]

            raise

        return data

    async def _respond(self, nonce, data):

        type = Types.RESPONSE

        data = await self._handle(data)

        await self._push(type, nonce, data)

    def _pull(self, type, nonce, data):

        if type == Types.REQUEST:

            coroutine = self._respond(nonce, data)

            self._loop.create_task(coroutine)

            return

        if type == Types.RESPONSE:

            future = self._waiters.pop(nonce)

            future.set_result(data)

            return

    async def start(self):

        generate = self._recv()

        async for data in generate:

            self._pull(*data)
