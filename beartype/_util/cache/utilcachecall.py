#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2020 Cecil Curry.
# See "LICENSE" for further details.

'''
**Beartype callable caching utilities.**

This private submodule implements supplementary cache-specific utility
functions required by various :mod:`beartype` facilities, including callables
generated by the :func:`beartype.beartype` decorator.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ IMPORTS                           }....................
import inspect
from beartype.roar import _BeartypeCallableCachedException
from functools import wraps
from inspect import Parameter

# ....................{ CONSTANTS ~ private               }....................
_PARAM_KINDS_UNSUPPORTED = {
    Parameter.VAR_KEYWORD,
    Parameter.VAR_POSITIONAL,
}
'''
Set of all :attr:`Parameter.kind` constants signifying parameter types *not*
currently supported by the :func:`callable_cached` decorator.
'''

# ....................{ CONSTANTS ~ private : sentinel    }....................
_SENTINEL_KWARGS_KEYS = (object(),)
'''
Sentinel tuple signifying subsequent keyword argument names.

This tuple is internally leveraged by the :func:`callable_cached` decorator to
differentiate keyword argument names from preceding positional arguments in the
flattened tuple of all parameters passed to the decorated callable.
'''


_SENTINEL_KWARGS_VALUES = (object(),)
'''
Sentinel tuple signifying subsequent keyword argument values.

This tuple is internally leveraged by the :func:`callable_cached` decorator to
differentiate keyword argument names from preceding positional arguments in the
flattened tuple of all parameters passed to the decorated callable.
'''

# ....................{ DECORATORS                        }....................
#FIXME: As needed, this callable may be generalized to support variadic
#parameters by appending to "params_flat":
#  1. A placeholder sentinel object after all positional and keyword arguments.
#  2. Those variadic parameters.

def callable_cached(func):
    '''
    **Memoize** (i.e., efficiently cache and return all previously returned
    values of the passed callable as well as all previously raised exceptions
    of that callable previously rather than inefficiently recalling that
    callable) the passed callable.

    Specifically, this decorator (in order):

    #. Creates:

       * A local dictionary mapping parameters passed to this callable with the
         values returned by this callable when passed those parameters.
       * A local dictionary mapping parameters passed to this callable with the
         exceptions raised by this callable when passed those parameters.

    #. Creates and returns a closure transparently wrapping this callable with
       memoization. Specifically, this wrapper (in order):

       #. Tests whether this callable has already been called at least once
          with the passed parameters by lookup of those parameters in these
          dictionaries.
       #. If this callable previously raised an exception when passed these
          parameters, this wrapper re-raises the same exception.
       #. Else if this callable returned a value when passed these parameters,
          this wrapper re-returns the same value.
       #. Else, this wrapper:

          #. Calls that callable with those parameters.
          #. If that call raised an exception:

             #. Caches that exception with those parameters in that dictionary.
             #. Raises that exception.

          #. Else:

             #. Caches the value returned by that call with those parameters in
                that dictionary.
             #. Returns that value.

    Caveats
    ----------
    **All parameters passed to the decorated callable must be hashable** (i.e.,
    immutable). Ergo, this decorator *cannot* memoize callables either
    accepting or returning mutable containers (e.g., `list`, `dict`).

    **No parameters accepted by the decorated callable may be variadic** (i.e.,
    either variadic positional or keyword arguments).

    **Order of keyword arguments passed to the decorated callable is
    significant.** This decorator recaches return values produced by calls to
    the decorated callable when passed the same keyword arguments in differing
    order (e.g., ``muh_func(muh_kw=0, mah_kw=1)`` and ``muh_func(mah_kw=1,
    muh_kw=0)``, cached as two distinct calls by this decorator despite these
    calls ultimately receiving the same arguments).

    **Maximize efficiency by only calling the decorated callable with
    positional arguments.** While calling this callable with keyword arguments
    is supported, doing so reduces the efficiency of the memoization performed
    by this decorator -- which is the whole point of this decorator, after all.

    Details
    ----------
    **This decorator is intentionally not implemented in terms of the stdlib**
    :func:`functools.lru_cache` **decorator,** as that decorator is inefficient
    in the special case of unbounded caching with ``maxsize=None``, mostly as
    that decorator insists on unconditionally recording irrelevant statistics
    such as cache misses and hits. While bounding the number of cached values
    is advisable in the general case (e.g., to avoid exhausting memory merely
    for optional caching), the callable parameters and return values cached by
    this package are sufficiently small in size to render bounding irrelevant.

    Consider the :func:`beartype._util.hint.pep.utilhintpeptest.is_hint_typing`
    function, for example. Each call to that function only accepts a single
    class and returns a boolean. Under conservative assumptions of 4 bytes of
    storage per class reference and 4 byte of storage per boolean reference,
    each call to that function requires caching at most 8 bytes of storage.
    Again, under conservative assumptions of at most 1024 unique type
    annotations for the average downstream consumer, memoizing that function in
    full requires at most 1024 * 8 == 8096 bytes or ~8Kb of storage. Clearly,
    8Kb of overhead is sufficiently negligible to obviate any space concerns
    that would warrant an LRU cache in the first place.

    Parameters
    ----------
    func : CallableTypes
        Callable to be memoized.

    Raises
    ----------
    _BeartypeCallableCachedException
        If any parameter passed to this callable is **variadic**: i.e., either

        * A variadic positional argument resembling ``*args``.
        * A variadic keyword argument resembling ``**kwargs``.

    Returns
    ----------
    CallableTypes
        Closure wrapping this callable with memoization..
    '''
    assert callable(func), '{!r} not callable.'.format(func)

    # Avoid circular import dependencies.
    from beartype._util.utilobj import SENTINEL

    # Human-readable name of this function for use in exceptions.
    func_name = '@callable_cached {}()'.format(func.__name__)

    # Signature of the decorated callable.
    func_sig = inspect.signature(func)

    # If the decorated callable accepts one or more variadic arguments, raise
    # an exception.
    for param in func_sig.parameters.values():
        if param.kind in _PARAM_KINDS_UNSUPPORTED:
            raise _BeartypeCallableCachedException(
                ' {}() parameter {} kind {!r} unsupported.'.format(
                    func_name, param.name, param.kind))

    # Dictionary mapping a tuple of all flattened parameters passed to each
    # prior call of the decorated callable with the value returned by that
    # call if any (i.e., if that call did *NOT* raise an exception).
    params_flat_to_return_value = {}

    # get() method of this dictionary, localized for efficiency.
    params_flat_to_return_value_get = params_flat_to_return_value.get

    # Dictionary mapping a tuple of all flattened parameters passed to each
    # prior call of the decorated callable with the exception raised by that
    # call if any (i.e., if that call raised an exception).
    params_flat_to_exception = {}

    # get() method of this dictionary, localized for efficiency.
    params_flat_to_exception_get = params_flat_to_exception.get

    @wraps(func)
    def _callable_cached(*args, **kwargs):
        '''
        Memoized variant of the {}() callable.

        Raises
        ----------
        TypeError
            If any parameter passed to this callable is **unhashable** (i.e.,
            mutable).

        See Also
        ----------
        :func:`callable_cached`
            Further details.
        '''.format(func.__name__)

        # Flatten the passed tuple of positional arguments and dictionary of
        # keyword arguments into a single tuple containing both positional and
        # keyword arguments. To minimize space consumption, this tuple contains
        # these arguments as is with *NO* nested containers.
        #
        # For example, when a decorated callable with signature:
        #    def muh_func(muh_arg1, muh_arg2, muh_arg3, muh_arg4)
        # ...is called as:
        #    muh_func('a', 'b', muh_arg3=0, muh_arg4=1)
        # ...this closure receives these variadic arguments:
        #    *args = ('a', 'b')
        #    *kwargs = {'muh_arg3': 0, 'muh_arg4': 1}
        # ...which the following logic flattens into this tuple:
        #    params_flat = (
        #        'a', 'b',
        #        _SENTINEL_KWARGS_KEYS, 'muh_arg3', 'muh_arg4',
        #        _SENTINEL_KWARGS_VALUES, 0, 1,
        #    )
        #
        # If one or more keyword arguments are passed, construct this flattened
        # tuple by concatenating together:
        #
        # * The passed tuple of positional arguments.
        # * A sentinel tuple differentiating the preceding positional arguments
        #   from subsequent keyword argument names.
        # * The names of all passed keyword arguments coerced into a tuple.
        # * A sentinel tuple differentiating the preceding keyword argument
        #   names from subsequent keyword argument values.
        # * The values of all passed keyword arguments coerced into a tuple.
        if kwargs:
            params_flat = (
                args +
                _SENTINEL_KWARGS_KEYS   + tuple(kwargs.keys()) +
                _SENTINEL_KWARGS_VALUES + tuple(kwargs.values())
            )
        # Else, only positional arguments are passed.
        #
        # If passed only one positional argument, minimize space consumption by
        # flattening this tuple of only that argument into that argument.
        elif len(args) == 1:
            params_flat = args[0]
        # Else, one or more positional arguments are passed. In this case,
        # reuse this tuple as is.
        else:
            params_flat = args

        # Exception raised by a prior call to the decorated callable when
        # passed these parameters *OR* the sentinel placeholder otherwise
        # (i.e., if this callable either has yet to be called with these
        # parameters *OR* has but failed to raise an exception).
        #
        # Note that this call raises a "TypeError" exception if any item of
        # this flattened tuple is unhashable.
        exception = params_flat_to_exception_get(params_flat, SENTINEL)

        # If this callable previously raised an exception when called with
        # these parameters, re-raise the same exception.
        if exception is not SENTINEL:
            raise exception
        # Else, this callable either has yet to be called with these parameters
        # *OR* has but failed to raise an exception.

        # Value returned by a prior call to the decorated callable when passed
        # these parameters *OR* the sentinel placeholder otherwise (i.e., if
        # this callable has yet to be called with these parameters).
        return_value = params_flat_to_return_value_get(params_flat, SENTINEL)

        # If this callable has already been called with these parameters,
        # return the value returned by that prior call.
        if return_value is not SENTINEL:
            return return_value
        # Else, this callable has yet to be called with these parameters.

        # Attempt to...
        try:
            # Call this parameter with these parameters and cache the value
            # returned by this call to these parameters.
            return_value = params_flat_to_return_value[params_flat] = func(
                *args, **kwargs)
        # If this call raises an exception...
        except Exception as exception:
            # Cache this exception to these parameters.
            params_flat_to_exception[params_flat] = exception

            # Re-raise this exception.
            raise exception

        # Return this value.
        return return_value

    # Return this wrapper.
    return _callable_cached
