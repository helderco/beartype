#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype warning hierarchy.**

This private submodule publishes a hierarchy of both public and private
:mod:`beartype`-specific warnings emitted at decoration, call, and usage time.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ IMPORTS                           }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To avoid polluting the public module namespace, external attributes
# should be locally imported at module scope *ONLY* under alternate private
# names (e.g., "from argparse import ArgumentParser as _ArgumentParser" rather
# than merely "from argparse import ArgumentParser").
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

from abc import ABCMeta as _ABCMeta

# See the "beartype.cave" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ SUPERCLASS                        }....................
class BeartypeWarning(UserWarning, metaclass=_ABCMeta):
    '''
    Abstract base class of all **beartype warnings.**

    Instances of subclasses of this warning are emitted either:

    * At decoration time from the :func:`beartype.beartype` decorator.
    * At call time from the new callable generated by the
      :func:`beartype.beartype` decorator to wrap the original callable.
    * At Sphinx-based documentation building time from Python code invoked by
      the ``doc/Makefile`` file.
    '''

    # ..................{ INITIALIZERS                      }..................
    def __init__(self, message: str) -> None:
        '''
        Initialize this exception.

        This constructor (in order):

        #. Passes all passed arguments as is to the superclass constructor.
        #. Sanitizes the fully-qualified module name of this
           exception from the private ``"beartype.roar._roarwarn"`` submodule
           to the public ``"beartype.roar"`` subpackage to both improve the
           readability of exception messages and discourage end users from
           accessing this private submodule.
        '''

        # Defer to the superclass constructor.
        super().__init__(message)

        # Sanitize the fully-qualified module name of the class of this
        # warning. See the docstring for justification.
        self.__class__.__module__ = 'beartype.roar'

# ....................{ DEPENDENCY                        }....................
class BeartypeDependencyOptionalMissingWarning(BeartypeWarning):
    '''
    **Beartype missing optional dependency warning.**

    This warning is emitted at various times to inform the user of a **missing
    recommended optional dependency** (i.e., third-party Python package *not*
    installed under the active Python interpreter whose installation is
    technically optional but recommended).
    '''

    pass

# ....................{ DECORATOR ~ hint : pep            }....................
class BeartypeDecorHintPepWarning(BeartypeWarning):
    '''
    Abstract base class of all **beartype decorator PEP-compliant type hint
    warnings.**

    Instances of subclasses of this warning are emitted at decoration time from
    the :func:`beartype.beartype` decorator on receiving a callable annotated
    by suspicious (but *not* necessarily erroneous) PEP-compliant type hints
    warranting non-fatal warnings *without* raising fatal exceptions.
    '''

    pass


class BeartypeDecorHintPepDeprecatedWarning(BeartypeDecorHintPepWarning):
    '''
    **Beartype decorator deprecated PEP-compliant type hint warning.**

    This warning is emitted at decoration time from the
    :func:`beartype.beartype` decorator on receiving a callable annotated by
    one or more **deprecated PEP-compliant type hints** (i.e., type hints
    compliant with outdated PEPs that have since been obsoleted by recent
    PEPs), including:

    * If the active Python interpreter targets at least Python >= 3.9 and thus
      supports `PEP 585`_, outdated `PEP 484`_-compliant type hints (e.g.,
      ``typing.List[int]``) that have since been obsoleted by the equivalent
      `PEP 585`_-compliant type hints (e.g., ``list[int]``).

    .. _PEP 484:
       https://www.python.org/dev/peps/pep-0484
    .. _PEP 585:
       https://www.python.org/dev/peps/pep-0585
    '''

    pass


#FIXME: Consider removal.
# class BeartypeDecorHintPepIgnorableDeepWarning(BeartypeDecorHintPepWarning):
#     '''
#     **Beartype decorator deeply ignorable PEP-compliant type hint warning.**
#
#     This warning is emitted at decoration time from the
#     :func:`beartype.beartype` decorator on receiving a callable annotated by
#     one or more **deeply ignorable PEP-compliant type hints** (i.e., instances or classes declared
#     by the stdlib :mod:`typing` module) currently unsupported by this
#     decorator.
#     '''
#
#     pass


#FIXME: Consider removal.
# class BeartypeDecorHintPepUnsupportedWarning(BeartypeWarning):
#     '''
#     **Beartype decorator unsupported PEP-compliant type hint warning.**
#
#     This warning is emitted at decoration time from the
#     :func:`beartype.beartype` decorator on receiving a callable annotated with
#     one or more PEP-compliant type hints (e.g., instances or classes declared
#     by the stdlib :mod:`typing` module) currently unsupported by this
#     decorator.
#     '''
#
#     pass

# ....................{ SPHINX                            }....................
#FIXME: Consider removal.
# class BeartypeSphinxWarning(BeartypeWarning, metaclass=_ABCMeta):
#     '''
#     Abstract base class of all **beartype Sphinx warnings.**
#
#     Instances of subclasses of this warning are emitted at Sphinx-based
#     documentation building time from the ``doc/Makefile`` file in various edge
#     cases warranting non-fatal warnings *without* raising fatal exceptions.
#     '''
#
#     pass

# ....................{ VALE                              }....................
class BeartypeValeWarning(BeartypeWarning):
    '''
    Abstract base class of all **beartype data validation warnings.**

    Instances of subclasses of this warning are emitted at usage (e.g.,
    instantiation, method call) time from the class hierarchy published by the
    :func:`beartype.vale` subpackage by suspicious (but *not* necessarily
    erroneous) PEP-compliant type hints warranting non-fatal warnings *without*
    raising fatal exceptions.
    '''

    pass


class BeartypeValeLambdaWarning(BeartypeValeWarning):
    '''
    **Beartype data validation lambda function warning.**

    This warning is emitted on passing the :func:`repr` builtin an instance of
    the :class:`beartype.vale.Is` class subscripted by a lambda function whose
    definition is *not* parsable from the script or module file defining that
    lambda.
    '''

    pass

# ....................{ PRIVATE ~ util                    }....................
class _BeartypeUtilWarning(BeartypeWarning):
    '''
    Abstract base class of all **beartype private utility warnings.**

    Instances of subclasses of this warning are emitted by *most* (but *not*
    all) private submodules of the private :mod:`beartype._util` subpackage.
    These warnings denote non-critical internal issues and should thus *never*
    be emitted, let alone allowed to percolate up the call stack to end users.
    '''

    pass

# ....................{ PRIVATE ~ util : call             }....................
class _BeartypeUtilCallableWarning(_BeartypeUtilWarning):
    '''
    **Beartype decorator memoization decorator keyword argument warnings.**

    This warning is emitted from callables memoized by the
    :func:`beartype._util.cache.utilcachecall.callable_cached` decorator on
    calls receiving one or more keyword arguments. Memoizing keyword arguments
    is substantially more space- and time-intensive than memoizing the
    equivalent positional arguments, partially defeating the purpose of
    memoization in the first place.

    This warning denotes a critical internal issue and should thus *never* be
    emitted to end users.
    '''

    pass


class _BeartypeUtilCallableCachedKwargsWarning(_BeartypeUtilCallableWarning):
    '''
    **Beartype decorator memoization decorator keyword argument warnings.**

    This warning is emitted from callables memoized by the
    :func:`beartype._util.cache.utilcachecall.callable_cached` decorator on
    calls receiving one or more keyword arguments. Memoizing keyword arguments
    is substantially more space- and time-intensive than memoizing the
    equivalent positional arguments, partially defeating the purpose of
    memoization in the first place.

    This warning denotes a critical internal issue and should thus *never* be
    emitted to end users.
    '''

    pass

