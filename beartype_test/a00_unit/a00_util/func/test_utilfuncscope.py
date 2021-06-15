#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**Callable scope utility unit tests.**

This submodule unit tests the public API of the private
:mod:`beartype._util.utilfunc.utilfuncscope` submodule.
'''

# ....................{ IMPORTS                           }....................
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: To raise human-readable test errors, avoid importing from
# package-specific submodules at module scope.
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
from pytest import raises

# ....................{ CLASSES                           }....................
class WhenOwlsCallTheBreathlessMoon(object):
    '''
    Arbitrary class declaring an arbitrary method.
    '''

    def in_the_blue_veil_of_the_night(self) -> None:
        '''
        Arbitrary method.
        '''

        pass


class TheShadowsOfTheTreesAppear(object):
    '''
    Arbitrary class declaring an arbitrary method.
    '''

    def amidst_the_lantern_light(self) -> None:
        '''
        Arbitrary method.
        '''

        pass

# ....................{ DECORATORS                        }....................
def decorator(func):
    '''
    Decorator attaching the local scope of the parent callable declaring the
    passed callable to a new ``func_locals`` attribute of the passed callable.
    '''

    # Defer scope-specific imports for sanity.
    from beartype._util.func.utilfuncscope import get_func_locals

    # Attach the local scope of that parent callable to the passed callable.
    func.func_locals = get_func_locals(func=func, func_stack_frames_ignore=1)

    # Reduce to the identity decorator.
    return func

# ....................{ CALLABLES                         }....................
def when_in_the_springtime_of_the_year():
    '''
    Arbitrary callable declaring an arbitrary nested callable.
    '''

    # Defer scope-specific imports for sanity.
    from typing import Union

    # Arbitrary PEP-compliant type hint localized to this parent callable.
    type_hint = Union[int, str]

    @decorator
    def when_the_trees_are_crowned_with_leaves() -> type_hint:
        '''
        Arbitrary nested callable annotated by a PEP-compliant type hint
        localized to the parent callable and decorated by a decorator attaching
        the local scope of that parent callable to a new ``func_locals``
        attribute of this nested callable.
        '''

        return 42

    # Return this nested callable.
    return when_the_trees_are_crowned_with_leaves

# ....................{ TESTS ~ tester                    }....................
def test_is_func_nested() -> None:
    '''
    Test the
    :func:`beartype._util.func.utilfuncscope.is_func_nested` function.
    '''

    # Defer heavyweight imports.
    from beartype._util.func.utilfuncscope import is_func_nested

    # Nested callable returned by the above callable.
    when_the_ash_and_oak_and_the_birch_and_yew = (
        when_in_the_springtime_of_the_year())

    # Assert this tester accepts methods.
    assert is_func_nested(
        WhenOwlsCallTheBreathlessMoon.in_the_blue_veil_of_the_night) is True

    # Assert this tester accepts nested callables.
    # print(f'__nested__: {repr(when_the_ash_and_oak_and_the_birch_and_yew.__nested__)}')
    assert is_func_nested(when_the_ash_and_oak_and_the_birch_and_yew) is True

    # Assert this tester rejects non-nested parent callables declaring nested
    # callables.
    # print(f'__nested__: {repr(when_in_the_springtime_of_the_year.__nested__)}')
    assert is_func_nested(when_in_the_springtime_of_the_year) is False

    # Assert this tester rejects C-based builtins.
    assert is_func_nested(iter) is False


#FIXME: Unclear whether we'll ever require this, but preserved as is for now.
# def test_get_func_wrappee() -> None:
#     '''
#     Test the
#     :func:`beartype._util.func.utilfuncget.get_func_wrappee` function.
#     '''
#
#     # Defer heavyweight imports.
#     from beartype.roar._roarexc import _BeartypeUtilCallableException
#     from beartype._util.func.utilfuncget import get_func_wrappee
#     from functools import wraps
#
#     # Arbitrary callable *NOT* decorated by @wraps.
#     def the_journey_begins_with_curiosity() -> str:
#         return 'And envolves into soul-felt questions'
#
#     # Arbitrary callable decorated by @wraps.
#     @wraps(the_journey_begins_with_curiosity)
#     def on_the_stones_that_we_walk() -> str:
#         return (
#             the_journey_begins_with_curiosity() +
#             'And choose to make our path'
#         )
#
#     # Assert this getter raises the expected exception when passed a callable
#     # *NOT* decorated by @wraps.
#     with raises(_BeartypeUtilCallableException):
#         get_func_wrappee(the_journey_begins_with_curiosity)
#
#     # Assert this getter returns the wrapped callable when passed a callable
#     # decorated by @wraps.
#     assert get_func_wrappee(on_the_stones_that_we_walk) is (
#         the_journey_begins_with_curiosity)

# ....................{ TESTS ~ getter                    }....................
def test_get_func_locals() -> None:
    '''
    Test the
    :func:`beartype._util.func.utilfuncscope.get_func_locals` function.
    '''

    # Defer heavyweight imports.
    from beartype.roar._roarexc import _BeartypeUtilCallableException
    from beartype._util.func.utilfuncmake import make_func
    from beartype._util.func.utilfuncscope import get_func_locals

    # Arbitrary nested callable dynamically declared in-memory.
    when_the_ash_and_oak_and_the_birch_and_yew = make_func(
        func_name='when_the_ash_and_oak_and_the_birch_and_yew',
        func_code='''def when_the_ash_and_oak_and_the_birch_and_yew(): pass''',
    )

    # Arbitrary nested callables whose unqualified and fully-qualified names
    # are maliciously desynchronized below, exercising edge cases.
    def are_dressed_in_ribbons_fair(): pass
    def in_the_blue_veil_of_the_night(): pass
    are_dressed_in_ribbons_fair.__qualname__ = (
        'when_owls_call.the_breathless_moon')
    in_the_blue_veil_of_the_night.__qualname__ = (
        '<locals>.in_the_blue_veil_of_the_night')

    # Assert this getter returns the empty dictionary for callables dynamically
    # declared in-memory.
    assert get_func_locals(when_the_ash_and_oak_and_the_birch_and_yew) == {}

    # Assert this getter returns the empty dictionary for unnested callables.
    assert get_func_locals(when_in_the_springtime_of_the_year) == {}

    # Arbitrary nested callable declared by an unnested callable.
    when_the_trees_are_crowned_with_leaves = (
        when_in_the_springtime_of_the_year())

    # Assert the local scope attached to this nested callable by its decorator
    # calling this getter contains the unqualified name of the local variable
    # annotating the return type of this nested callable.
    assert 'type_hint' in when_the_trees_are_crowned_with_leaves.func_locals

    # Assert this getter raises the expected exception for nested callables
    # whose unqualified and fully-qualified names are desynchronized.
    with raises(_BeartypeUtilCallableException):
        get_func_locals(are_dressed_in_ribbons_fair)

    # Assert this getter raises the expected exception for nested callables
    # whose fully-qualified name is prefixed by "<locals>".
    with raises(_BeartypeUtilCallableException):
        get_func_locals(in_the_blue_veil_of_the_night)

# ....................{ TESTS ~ adder                     }....................
def test_add_func_scope_attr() -> None:
    '''
    Test the
    :func:`beartype._util.func.utilfuncscope.add_func_scope_attr` function.
    '''

    # Defer heavyweight imports.
    from beartype._util.func.utilfuncscope import add_func_scope_attr

    # Arbitrary scope to add attributes to.
    attr_scope = {}

    # Arbitrary object to be added to this scope.
    attr = 'Pestilence-stricken multitudes: O thou,'

    # Named of this attribute in this scope.
    attr_name = add_func_scope_attr(attr=attr, attr_scope=attr_scope)

    # Assert the prior call added this attribute to this scope as expected.
    assert isinstance(attr_name, str)
    assert str(id(attr)) in attr_name
    assert attr_scope[attr_name] is attr

    # Assert this getter returns the same name when repassed an attribute
    # previously added to this scope.
    assert add_func_scope_attr(attr=attr, attr_scope=attr_scope) == attr_name
    assert attr_scope[attr_name] is attr

    # Note that testing this getter's error condition is effectively
    # infeasible, as doing so would require deterministically creating a
    # different object with the same object identifier. *sigh*

# ....................{ TESTS ~ adder : type              }....................
def test_add_func_scope_type_pass() -> None:
    '''
    Test successful usage of the
    :func:`beartype._util.func.utilfuncscope.add_func_scope_type` function.
    '''

    # Defer heavyweight imports.
    from beartype.roar._roarexc import _BeartypeDecorBeartypistryException
    from beartype._cave._cavefast import NoneType, RegexCompiledType
    from beartype._util.func.utilfuncscope import add_func_scope_type
    from beartype._util.utilobject import get_object_type_basename

    # Arbitrary scope to be added to below.
    cls_scope = {}

    # Assert this function supports...
    classes_nonbuiltin = (
        # Adding a non-builtin type.
        RegexCompiledType,
        # Readding that same type.
        RegexCompiledType,
        # Adding the type of the "None" singleton (despite technically being
        # listed as belonging to the "builtin" module) under a unique name
        # rather than its unqualified basename "NoneType" (which doesn't
        # actually exist, which is inconsistent nonsense, but whatever).
        NoneType,
    )
    for cls in classes_nonbuiltin:
        cls_scope_name = add_func_scope_type(cls=cls, cls_scope=cls_scope)
        assert cls_scope_name != get_object_type_basename(cls)
        assert cls_scope[cls_scope_name] is cls

    # Assert this function does *NOT* add builtin types but instead simply
    # returns the unqualified basenames of those types.
    cls = list
    cls_scope_name = add_func_scope_type(cls=cls, cls_scope=cls_scope)
    assert cls_scope_name == get_object_type_basename(cls)
    assert cls_scope_name not in cls_scope


def test_add_func_scope_type_fail() -> None:
    '''
    Test unsuccessful usage of the
    :func:`beartype._util.func.utilfuncscope.add_func_scope_type` function.
    '''

    # Defer heavyweight imports.
    from beartype.roar import BeartypeDecorHintPep3119Exception
    from beartype._util.func.utilfuncscope import add_func_scope_type
    from beartype_test.a00_unit.data.data_type import NonIsinstanceableClass

    # Arbitrary scope to be added to below.
    cls_scope = {}

    # Assert this function raises the expected exception for non-types.
    with raises(BeartypeDecorHintPep3119Exception):
        add_func_scope_type(
            cls=(
                'The best lack all conviction, while the worst',
                'Are full of passionate intensity',
            ),
            cls_scope=cls_scope,
        )

    # Assert this function raises the expected exception for PEP 560-compliant
    # classes whose metaclasses define an __instancecheck__() dunder method to
    # unconditionally raise exceptions.
    with raises(BeartypeDecorHintPep3119Exception):
        add_func_scope_type(cls=NonIsinstanceableClass, cls_scope=cls_scope)

# ....................{ TESTS ~ adder : tuple             }....................
def test_add_func_scope_types_pass() -> None:
    '''
    Test successful usage of the
    :func:`beartype._util.func.utilfuncscope.add_func_scope_types` function.
    '''

    # Defer heavyweight imports.
    from beartype.roar._roarexc import _BeartypeDecorBeartypistryException
    from beartype._cave._cavefast import CallableTypes, ModuleOrStrTypes
    from beartype._cave._cavemap import NoneTypeOr
    from beartype._util.func.utilfuncscope import add_func_scope_types
    from beartype._util.utilobject import get_object_type_basename

    # Arbitrary scope to be added to below.
    types_scope = {}

    # Assert this function adds a tuple of one or more standard types.
    #
    # Note that, unlike types, tuples are internally added under different
    # objects than their originals (e.g., to ignore both duplicates and
    # ordering) and *MUST* thus be tested by conversion to sets.
    types = CallableTypes
    types_scope_name = add_func_scope_types(
        types=types, types_scope=types_scope)
    assert set(types) == set(types_scope[types_scope_name])

    # Assert this function readds the same tuple as well.
    types_scope_name_again = add_func_scope_types(
        types=types, types_scope=types_scope)
    assert types_scope_name == types_scope_name_again

    # Assert this function adds a frozenset of one or more standard types.
    types = frozenset(ModuleOrStrTypes)
    types_scope_name = add_func_scope_types(
        types=types, types_scope=types_scope)
    assert set(types) == set(types_scope[types_scope_name])

    # Assert this function does *NOT* add tuples of one non-builtin types but
    # instead simply returns the unqualified basenames of those types.
    types = (int,)
    types_scope_name = add_func_scope_types(
        types=types, types_scope=types_scope)
    assert types_scope_name == get_object_type_basename(types[0])
    assert types_scope_name not in types_scope

    # Assert this function adds tuples of one non-builtin type as merely that
    # type rather than that tuple.
    types = (WhenOwlsCallTheBreathlessMoon,)
    types_scope_name = add_func_scope_types(
        types=types, types_scope=types_scope)
    assert types_scope[types_scope_name] is WhenOwlsCallTheBreathlessMoon

    # Assert this function adds tuples containing duplicate types as tuples
    # containing only the proper subset of non-duplicate types.
    types = (TheShadowsOfTheTreesAppear,)*3
    types_scope_name = add_func_scope_types(
        types=types, types_scope=types_scope)
    assert types_scope[types_scope_name] == (TheShadowsOfTheTreesAppear,)

    # Assert this function registers tuples containing *NO* duplicate types.
    types = NoneTypeOr[CallableTypes]
    types_scope_name = add_func_scope_types(
        types=types, types_scope=types_scope, is_unique=True)
    assert types_scope[types_scope_name] == types

    #FIXME: Disable this until we drop Python 3.6 support. While Python >= 3.7
    #preserves insertion order for sets, Python < 3.7 does *NOT*.
    # # Assert that tuples of the same types but in different orders are
    # # registrable via the same function but reduce to differing objects.
    # hint_a = (int, str,)
    # hint_b = (str, int,)
    # hint_cached_a = _eval_registered_expr(register_typistry_tuple(hint_a))
    # hint_cached_b = _eval_registered_expr(register_typistry_tuple(hint_b))
    # assert hint_cached_a != hint_cached_b


def test_add_func_scope_types_fail() -> None:
    '''
    Test successful usage of the
    :func:`beartype._util.func.utilfuncscope.add_func_scope_types` function.
    '''

    # Defer heavyweight imports
    from beartype.roar import (
        BeartypeDecorHintNonPepException,
        BeartypeDecorHintPep3119Exception,
    )
    from beartype._util.func.utilfuncscope import add_func_scope_types
    from beartype_test.a00_unit.data.data_type import NonIsinstanceableClass
    from beartype_test.a00_unit.data.hint.pep.proposal.data_hintpep484 import (
        Pep484GenericTypevaredSingle)

    # Arbitrary scope to be added to below.
    types_scope = {}

    # Assert this function raises the expected exception for unhashable tuples.
    with raises(BeartypeDecorHintNonPepException):
        add_func_scope_types(
            types=(
                int, str, {
                    'Had': "I the heaven’s embroidered cloths,",
                    'Enwrought': "with golden and silver light,",
                    'The': 'blue and the dim and the dark cloths',
                    'Of': 'night and light and the half-light,',
                    'I': 'would spread the cloths under your feet:',
                    'But': 'I, being poor, have only my dreams;',
                    'I have': 'spread my dreams under your feet;',
                    'Tread': 'softly because you tread on my dreams.',
                },
            ),
            types_scope=types_scope,
        )

    # Assert this function raises the expected exception for non-tuples.
    with raises(BeartypeDecorHintNonPepException):
        add_func_scope_types(
            types='\n'.join((
                'I will arise and go now, and go to Innisfree,',
                'And a small cabin build there, of clay and wattles made;',
                'Nine bean-rows will I have there, a hive for the honey-bee,',
                'And live alone in the bee-loud glade.',
            )),
            types_scope=types_scope,
        )

    # Assert this function raises the expected exception for empty tuples.
    with raises(BeartypeDecorHintNonPepException):
        add_func_scope_types(types=(), types_scope=types_scope)

    # Assert this function raises the expected exception for tuples containing
    # one or more PEP-compliant types.
    with raises(BeartypeDecorHintNonPepException):
        add_func_scope_types(
            types=(int, Pep484GenericTypevaredSingle, str,),
            types_scope=types_scope,
        )

    # Assert this function raises the expected exception for tuples containing
    # one or more PEP 560-compliant classes whose metaclasses define an
    # __instancecheck__() dunder method to unconditionally raise exceptions.
    with raises(BeartypeDecorHintNonPepException):
        add_func_scope_types(
            types=(bool, NonIsinstanceableClass, float,),
            types_scope=types_scope,
        )