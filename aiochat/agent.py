import functools

from . import helpers


__all__ = ('Error', 'UnknownError', 'InvalidError', 'FailureError', 'use',
           'Agent')


class Error(Exception):

    __slots__ = ()


class UnknownError(Error):

    __slots__ = ()

    def __init__(self, data):

        message = 'Wrong method.'

        super().__init__(message)


class InvalidError(Error):

    __slots__ = ()

    def __init__(self, data):

        if isinstance(data, int):

            amount = abs(data)

            detail = 'more' if data < 0 else 'less'

            message = f'Got {amount} {detail} positional arguments'

        elif isinstance(data, list):

            message = f'Extra keyword arguments {data}'

        else:

            raise TypeError('Unknown data type')

        super().__init__(message)


class FailureError(Error):

    __slots__ = ()

    def __init__(self, data):

        message = f'Call failed with {data}'

        super().__init__(message)


class Types:

    UNKNOWN = 0
    INVALID = 1
    FAILURE = 2
    SUCCESS = 3


errors = {
    Types.UNKNOWN: UnknownError,
    Types.INVALID: InvalidError,
    Types.FAILURE: FailureError
}


exposed = set()


def use(value):

    exposed.add(value)

    return value


class AgentMeta(type):

    def __new__(cls, name, bases, namespace):

        details = {}

        for base in bases:

            if not isinstance(base, cls):

                continue

            details.update(base._details)

        for (key, value) in namespace.items():

            try:

                exposed.remove(value)

            except (KeyError, TypeError):

                continue

            if key.startswith('_'):

                raise ValueError('Methods cannot start with _')

            spec = helpers.spec(value)

            details[value] = spec

        namespace = dict(namespace)

        self = super().__new__(cls, name, bases, namespace)

        self._details = details

        return self


class Agent(metaclass = AgentMeta):

    __slots__ = ('_channel',)

    def bind(self, channel):

        self._channel = channel

        channel.bind(self._handle)

    async def _trigger(self, name, *args, **kwargs):

        data = (name, args, kwargs)

        (type, data) = await self._channel.request(data)

        try:

            error = errors[type]

        except KeyError:

            return data

        raise error(data)

    async def _handle(self, data):

        (name, args, kwargs) = data

        try:

            method = getattr(self, name)

            function = method.__func__

            spec = self._details[function]

        except (AttributeError, KeyError):

            return (Types.UNKNOWN, None)

        if not spec.varargs:

            left = len(spec.args) - len(args)

            left -= 1 # self

            if left:

                data = left

                return (Types.INVALID, data)

        if not spec.varkwargs:

            extra = set(kwargs).difference(spec.kwargs)

            if extra:

                data = tuple(extra)

                return (Types.INVALID, data)

        try:

            data = await method(*args, **kwargs)

        except Error as error:

            return (Types.FAILURE, error.args)

        return (Types.SUCCESS, data)

    def __getattr__(self, name):

        return functools.partial(self._trigger, name)
