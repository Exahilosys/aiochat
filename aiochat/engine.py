import asyncio
import json

from . import channel
from . import agent


__all__ = ('ClientAgent', 'ServerAgent')


class Agent(agent.Agent):

    __slots__ = ()

    def __init__(self, loop = None):

        if not loop:

            loop = asyncio.get_event_loop()

        future = loop.create_future()

        future.cancel()

        self._task = future

        self._loop = loop

    def start(self, source):

        self.bind(source)

        coroutine = source.start()

        self._task = self._loop.create_task(coroutine)

    def wait(self):

        return self._task

    def stop(self):

        self._task.cancel()


class WebSocketAgent(Agent):

    __slots__ = ('_encode', '_decode', '_websocket')

    def __init__(self,
                 *args,
                 encode = json.dumps,
                 decode = json.loads,
                 **kwargs):

        super().__init__(*args, **kwargs)

        self._encode = encode

        self._decode = decode

        self._websocket = None

    async def _send(self, data):

        data = self._encode(data)

        await self._websocket.send_str(data)

    async def _recv(self):

        while True:

            try:

                message = await self._websocket.__anext__()

            except (asyncio.CancelledError, StopAsyncIteration):

                break

            data = self._decode(message.data)

            yield data

    async def start(self, websocket):

        self._websocket = websocket

        source = channel.Channel(self._send, self._recv, loop = self._loop)

        return super().start(source)

    async def stop(self):

        super().stop()

        await self._websocket.close()


class ClientAgent(WebSocketAgent):

    __slots__ = ('_connect', '_interval', '_greet', '_restart')

    _timeout = 2

    def __init__(self, connect, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self._connect = connect

        self._interval = None

        self._greet = asyncio.Event(loop = self._loop)

        self._restart = asyncio.Event(loop = self._loop)

    @property
    def _stopped(self):

        return not self._greet.is_set()

    async def wait(self):

        while True:

            await super().wait()

            if self._stopped:

                break

            await self._restart.wait()

    @agent.use
    async def hello(self, interval):

        self._interval = interval

        self._greet.set()

    async def _pulse(self):

        self._restart.clear()

        while not self._websocket.closed:

            coroutine = self.alert()

            try:

                await asyncio.wait_for(coroutine, timeout = self._timeout)

            except asyncio.TimeoutError:

                break

            try:

                await asyncio.sleep(self._interval - 3)

            except asyncio.CancelledError:

                pass

        if self._stopped:

            return

        await self.stop()

        await self.start()

        self._restart.set()

    async def start(self):

        websocket = await self._connect()

        await super().start(websocket)

        await self._greet.wait()

        coroutine = self._pulse()

        pulsing = self._loop.create_task(coroutine)

        callback = lambda *args: pulsing.cancel()

        self._task.add_done_callback(callback)

    async def stop(self):

        self._greet.clear()

        await super().stop()


class ServerAgent(WebSocketAgent):

    __slots__ = ('_interval', '_expect', '_stop')

    def __init__(self, interval = 60, **kwargs):

        super().__init__(**kwargs)

        self._interval = interval

        self._expect = 0

        self._decide = False

    @agent.use
    async def alert(self):

        time = self._loop.time()

        update = time > self._expect

        if update:

            self._expect = self._loop.time() + self._interval

        return update

    async def start(self, *args, **kwargs):

        await super().start(*args, **kwargs)

        await self.hello(self._interval)
