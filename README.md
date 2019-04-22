## Server Usage
```py
import aiochat
import aiohttp.web

class Agent(aiochat.ServerAgent):

    @aiochat.use
    async def join(self, *args, delimit = ','):

        return delimit.join(map(str, args))

app = aiohttp.web.Application()

routes = aiohttp.web.RouteTableDef()

@routes.get('/connect')
async def handle(request):

    websocket = aiohttp.web.WebSocketResponse()

    await websocket.prepare(request)

    agent = Agent()

    await agent.start(websocket)

    value = 'eggs and bacon and salad'

    # remote call
    result = await agent.split(value, delimit = ' and ')

    print('result:', result)

    # wait until disconnection
    await agent.wait()

    return websocket

app.router.add_routes(routes)

aiohttp.web.run_app(app)
```
## Client Usage
```py
import aiochat
import aiohttp
import asyncio

class Agent(aiochat.ClientAgent):

    @aiochat.use
    async def split(self, value, delimit = ','):

        return value.split(delimit)

loop = asyncio.get_event_loop()

url = 'http://localhost:8080/connect'

async def main():

    session = aiohttp.ClientSession(loop = loop)

    async def connect():

        while not session.closed:

            try:

                websocket = await session.ws_connect(url)

            except aiohttp.ClientError:

                await asyncio.sleep(0.5)

            else:

                break

        return websocket

    agent = Agent(connect)

    await agent.start()

    values = ('crooked man', 'mile', 'sixpence', 'stile')

    # remote call
    result = await agent.join(*values, delimit = ' ')

    print('result:', result)

    # disconnect
    await agent.stop()

    await session.close()

coroutine = main()

loop.run_until_complete(coroutine)
```
## Details
- Clients will attempt to auto-reconnect until told to stop.
- Method names have to follow python function name limitations.
- The reconnection protocol reserves the `hello` `alert` methods.
- Implementation reserves the `bind` `wait` `start` `stop` methods.
- Annotations are not considered; schema checking should be done manually.
- Keyword arguments cannot be passed in a positional manner and vice versa.
- WebSockets should not be used outside of Agent context while connected.
## Installing
```
python3 -m pip install aiochat
```
