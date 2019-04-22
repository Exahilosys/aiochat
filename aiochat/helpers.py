import itertools
import collections
import inspect


__all__ = ()


def unique(store):

    predicate = store.__contains__

    available = itertools.count()

    generate = itertools.filterfalse(predicate, available)

    value = next(generate)

    return value


_Spec = collections.namedtuple('Spec', 'args kwargs varargs varkwargs')


def spec(function):

    signature = inspect.signature(function)

    (pos, kw, vpos, vkw) = ([], [], False, False)

    for value in signature.parameters.values():

        if value.kind is value.VAR_POSITIONAL:

            vpos = True

            continue

        if value.kind is value.VAR_KEYWORD:

            vkw = True

            continue

        if value.default is value.empty:

            pos.append(value.name)

            continue

        kw.append(value.name)

    stores = (pos, kw)

    (pos, kw) = map(tuple, stores)

    return _Spec(pos, kw, vpos, vkw)
