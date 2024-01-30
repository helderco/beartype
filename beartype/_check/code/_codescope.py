#!/usr/bin/env python3
# --------------------( LICENSE                            )--------------------
# Copyright (c) 2014-2024 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype decorator PEP-compliant code wrapper scope utilities** (i.e.,
functions handling the possibly nested lexical scopes enclosing wrapper
functions generated by the :func:`beartype.beartype` decorator).

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                               }....................
#FIXME: Hah-hah! Finally figured out how to do recursive type hints... mostly.
#It's a two-parter consisting of:
#* *PART I.* In the first part:
#  * Refactor our code generation algorithm to additionally maintain a stack of
#    all parent type hints of the currently visited type hint. Note that we need
#    to do this anyway to support the __beartype_hint__() protocol. See "FIXME:"
#    comments in the "beartype.plug._plughintable" submodule pertaining to that
#    protocol for further details on properly building out this stack.
#  * When that algorithm visits a forward reference:
#    * That algorithm calls the express_func_scope_type_forwardref() function
#      generating type-checking code for that reference. Refactor that call to
#      additionally pass that stack of parent hints to that function.
#    * Refactor the express_func_scope_type_forwardref() function to:
#      * If the passed forward reference is relative, additionally return that
#        stack in the returned 3-tuple
#        "(forwardref_expr, forwardrefs_class_basename, forwardref_parent_hints)",
#        where "forwardref_parent_hints" is that stack.
#* *PART II.* In the second part:
#  * Refactor the beartype._decor.wrap.wrapmain._unmemoize_func_wrapper_code()
#    function to additionally:
#    * If the passed forward reference is relative *AND* the unqualified
#      basename of an existing attribute in a local or global scope of the
#      currently decorated callable *AND* the value of that attribute is a
#      parent type hint on the stack of parent type hints returned by the
#      previously called express_func_scope_type_forwardref() function, then
#      *THIS REFERENCE INDICATES A RECURSIVE TYPE HINT.* In this case:
#      * Replace this forward reference with a new recursive type-checking
#        "beartype._check.forward.fwdref.BeartypeForwardRef_{forwardref}"
#        subclass whose is_instance() tester method recursively calls itself
#        indefinitely. If doing so generates a "RecursionError", @beartype
#        considers that the user's problem. *wink*
#
#Done and done. Phew!

# ....................{ IMPORTS                            }....................
from beartype.roar import BeartypeDecorHintNonpepException
from beartype._cave._cavemap import NoneTypeOr
from beartype._data.hint.datahinttyping import LexicalScope
from beartype._check.forward.fwdtype import (
    TYPISTRY_HINT_NAME_TUPLE_PREFIX,
    bear_typistry,
    get_hint_forwardref_code,
)
from beartype._check.checkmagic import ARG_NAME_TYPISTRY
from beartype._check.code.codesnip import (
    CODE_HINT_REF_TYPE_BASENAME_PLACEHOLDER_PREFIX,
    CODE_HINT_REF_TYPE_BASENAME_PLACEHOLDER_SUFFIX,
)
from beartype._util.cls.pep.utilpep3119 import die_unless_type_isinstanceable
from beartype._util.cls.utilclstest import is_type_builtin
from beartype._util.func.utilfuncscope import add_func_scope_attr
from beartype._util.hint.nonpep.utilnonpeptest import (
    die_unless_hint_nonpep_type)
from beartype._util.hint.pep.proposal.pep484585.utilpep484585ref import (
    Pep484585ForwardRef,
    die_unless_hint_pep484585_ref,
    get_hint_pep484585_ref_name,
)
from beartype._util.utilobject import get_object_type_basename
from beartype._data.hint.datahinttyping import (
    TypeOrTupleTypes,
    TupleTypes,
)
from collections.abc import Set
from typing import AbstractSet, Optional, Tuple, Union

# ....................{ PRIVATE                            }....................
_SET_OR_TUPLE = (Set, tuple)
'''
2-tuple containing the superclasses of all frozen sets and tuples.

Note that the :class:`Set` abstract base class (ABC) rather than the concrete
:class:`set` subclass is intentionally listed here, as the concrete
:class:`frozenset` subclass subclasses the former but *not* latter: e.g.,

.. code-block:: python

   >>> from collections.abc import Set
   >>> issubclass(frozenset, Set)
   True
   >>> issubclass(frozenset, set)
   False
'''


_SetOrTupleOfTypes = Union[AbstractSet[type], TupleTypes]
'''
PEP-compliant type hint matching a set *or* tuple of zero or more classes.
'''

# ....................{ ADDERS ~ type                      }....................
#FIXME: Unit test us up, please.
def add_func_scope_type_or_types(
    # Mandatory parameters.
    type_or_types: TypeOrTupleTypes,
    func_scope: LexicalScope,

    # Optional parameters.
    exception_prefix: str = (
        'Globally or locally scoped class or tuple of classes '),
) -> str:
    '''
    Add a new **scoped class or tuple of classes** (i.e., new key-value pair of
    the passed dictionary mapping from the name to value of each globally or
    locally scoped attribute externally accessed elsewhere, whose key is a
    machine-readable name internally generated by this function to uniquely
    refer to the passed class or tuple of classes and whose value is that class
    or tuple) to the passed scope *and* return that name.

    This function additionally caches this tuple with the beartypistry
    singleton to reduce space consumption for tuples duplicated across the
    active Python interpreter.

    Parameters
    ----------
    type_or_types : TypeOrTupleTypes
        Arbitrary class or tuple of classes to be added to this scope.
    func_scope : LexicalScope
        Local or global scope to add this class or tuple of classes to.
    exception_prefix : str, optional
        Human-readable label prefixing the representation of this object in the
        exception message. Defaults to the empty string.

    Returns
    -------
    str
        Name of this class or tuple in this scope generated by this function.

    Raises
    ------
    BeartypeDecorHintNonpepException
        If this hint is either:

        * Neither a class nor tuple.
        * A tuple that is empty.
    BeartypeDecorHintPep3119Exception
        If hint is:

        * A class that is *not* isinstanceable (i.e., passable as the second
          argument to the :func:`isinstance` builtin).
        * A tuple of one or more items that are *not* isinstanceable classes.
    _BeartypeUtilCallableException
        If an attribute with the same name as that internally generated by this
        adder but having a different value already exists in this scope. This
        adder uniquifies names by object identifier and should thus *never*
        generate name collisions. This exception is thus intentionally raised
        as a private rather than public exception.
    '''

    # Return either...
    return (
        # If this hint is a class, the name of a new parameter passing this
        # class;
        add_func_scope_type(
            cls=type_or_types,
            func_scope=func_scope,
            exception_prefix=exception_prefix,
        )
        if isinstance(type_or_types, type) else
        # Else, this hint is *NOT* a class. In this case:
        # * If this hint is a tuple of classes, the name of a new parameter
        #   passing this tuple.
        # * Else, raise an exception.
        add_func_scope_types(
            types=type_or_types,
            func_scope=func_scope,
            exception_prefix=exception_prefix,
        )
    )


def add_func_scope_type(
    # Mandatory parameters.
    cls: type,
    func_scope: LexicalScope,

    # Optional parameters.
    exception_prefix: str = 'Globally or locally scoped class ',
) -> str:
    '''
    Add a new **scoped class** (i.e., new key-value pair of the passed
    dictionary mapping from the name to value of each globally or locally
    scoped attribute externally accessed elsewhere, whose key is a
    machine-readable name internally generated by this function to uniquely
    refer to the passed class and whose value is that class) to the passed
    scope *and* return that name.

    Parameters
    ----------
    cls : type
        Arbitrary class to be added to this scope.
    func_scope : LexicalScope
        Local or global scope to add this class to.
    exception_prefix : str, optional
        Human-readable label prefixing the representation of this object in the
        exception message. Defaults to the empty string.

    Returns
    -------
    str
        Name of this class in this scope generated by this function.

    Raises
    ------
    BeartypeDecorHintPep3119Exception
        If this class is *not* isinstanceable (i.e., passable as the second
        argument to the :func:`isinstance` builtin).
    _BeartypeUtilCallableException
        If an attribute with the same name as that internally generated by this
        adder but having a different value already exists in this scope. This
        adder uniquifies names by object identifier and should thus *never*
        generate name collisions. This exception is thus intentionally raised
        as a private rather than public exception.
    '''

    # If this object is *NOT* an isinstanceable class, raise an exception.
    die_unless_type_isinstanceable(cls=cls, exception_prefix=exception_prefix)
    # Else, this object is an isinstanceable class.

    # Return either...
    return (
        # If this type is a builtin (i.e., globally accessible C-based type
        # requiring *no* explicit importation), the unqualified basename of
        # this type as is, as this type requires no parametrization;
        get_object_type_basename(cls)
        if is_type_builtin(cls) else
        # Else, the name of a new parameter passing this class.
        add_func_scope_attr(
            attr=cls, func_scope=func_scope, exception_prefix=exception_prefix)
    )


def add_func_scope_types(
    # Mandatory parameters.
    types: _SetOrTupleOfTypes,
    func_scope: LexicalScope,

    # Optional parameters.
    is_unique: bool = False,
    exception_prefix: str = (
        'Globally or locally scoped set or tuple of classes '),
) -> str:
    '''
    Add a new **scoped tuple of classes** (i.e., new key-value pair of the
    passed dictionary mapping from the name to value of each globally or
    locally scoped attribute externally accessed elsewhere, whose key is a
    machine-readable name internally generated by this function to uniquely
    refer to the passed set or tuple of classes and whose value is that tuple)
    to the passed scope *and* return that machine-readable name.

    This function additionally caches this tuple with the beartypistry
    singleton to reduce space consumption for tuples duplicated across the
    active Python interpreter.

    Design
    ----------
    Unlike types, tuples are commonly dynamically constructed on-the-fly by
    various tuple factories (e.g., :attr:`beartype.cave.NoneTypeOr`,
    :attr:`typing.Optional`) and hence have no reliable fully-qualified names.
    Instead, this function caches this tuple into the beartypistry under a
    string synthesized as the unique concatenation of:

    * The magic substring :data:`TYPISTRY_HINT_NAME_TUPLE_PREFIX`. Since
      fully-qualified classnames uniquely identifying types as beartypistry
      keys are guaranteed to *never* contain this substring, this substring
      prevents collisions between tuple and type names.
    * This tuple's hash. Note that this tuple's object ID is intentionally
      *not* embedded in this string. Two tuples with the same items are
      typically different objects and thus have different object IDs, despite
      producing identical hashes: e.g.,

      >>> ('Das', 'Kapitel',) is ('Das', 'Kapitel',)
      False
      >>> id(('Das', 'Kapitel',)) == id(('Das', 'Kapitel',))
      False
      >>> hash(('Das', 'Kapitel',)) == hash(('Das', 'Kapitel',))
      True

    The exception is the empty tuple, which is a singleton and thus *always*
    has the same object ID and hash: e.g.,

        >>> () is ()
        True
        >>> id(()) == id(())
        True
        >>> hash(()) == hash(())
        True

    Identifying tuples by their hashes enables the beartypistry singleton to
    transparently cache duplicate class tuples with distinct object IDs as the
    same underlying object, reducing space consumption. While hashing tuples
    does impact time performance, the gain in space is worth the cost.

    Parameters
    ----------
    types : _SetOrTupleOfTypes
        Set or tuple of arbitrary types to be added to this scope.
    func_scope : LexicalScope
        Local or global scope to add this object to.
    is_unique : bool, optional
        ``True`` only if the caller guarantees this tuple to contain *no*
        duplicate types. This boolean is ignored if ``types`` is a set rather
        than tuple. Defaults to ``False``. If ``False``, this function assumes
        this tuple to contain duplicate types by internally:

        #. Coercing this tuple into a set, thus implicitly ignoring both
           duplicates and ordering of types in this tuple.
        #. Coercing that set back into another tuple.
        #. If these two tuples differ, the passed tuple contains one or more
           duplicates; in this case, the duplicate-free tuple is cached and
           passed.
        #. Else, the passed tuple contains no duplicates; in this case, the
           passed tuple is cached and passed.

        This boolean does *not* simply enable an edge-case optimization, though
        it certainly does that; this boolean enables callers to guarantee that
        this function caches and passes the passed tuple rather than a new
        tuple internally created by this function.
    exception_prefix : str, optional
        Human-readable label prefixing the representation of this object in the
        exception message. Defaults to the empty string.

    Returns
    -------
    str
        Name of this tuple in this scope generated by this function.

    Raises
    ------
    BeartypeDecorHintNonpepException
        If this hint is either:

        * Neither a set nor tuple.
        * A set or tuple that is empty.
    BeartypeDecorHintPep3119Exception
        If one or more items of this hint are *not* isinstanceable classes
        (i.e., classes passable as the second argument to the
        :func:`isinstance` builtin).
    _BeartypeUtilCallableException
        If an attribute with the same name as that internally generated by this
        adder but having a different value already exists in this scope. This
        adder uniquifies names by object identifier and should thus *never*
        generate name collisions. This exception is thus intentionally raised
        as a private rather than public exception.
    '''
    assert is_unique.__class__ is bool, f'{repr(is_unique)} not bool.'

    # If this object is neither a set nor tuple, raise an exception.
    if not isinstance(types, _SET_OR_TUPLE):
        raise BeartypeDecorHintNonpepException(
            f'{exception_prefix}{repr(types)} neither set nor tuple.')
    # Else, this object is either a set or tuple.
    #
    # If this collection is empty, raise an exception.
    elif not types:
        raise BeartypeDecorHintNonpepException(f'{exception_prefix}empty.')
    # Else, this collection is non-empty.

    #FIXME: *EXCEPTIONALLY INEFFICIENT.* Let's optimize this sometime, please.
    # If any item in this collection is *NOT* an isinstanceable class, raise an
    # exception.
    for cls in types:
        die_unless_hint_nonpep_type(
            hint=cls, exception_prefix=exception_prefix)
    # Else, all items of this collection are isinstanceable classes.

    # If this tuple only contains one type, register only this type.
    if len(types) == 1:
        return add_func_scope_type(
            # The first and only item of this collection, accessed as either:
            # * If this collection is a tuple, that item with fast indexing.
            # * If this collection is a set, that item with slow iteration.
            cls=types[0] if isinstance(types, tuple) else next(iter(types)),
            func_scope=func_scope,
            exception_prefix=exception_prefix,
        )
    # Else, this tuple either contains two or more types.
    #
    # If this collection is a frozenset, coerce this frozenset into a tuple.
    elif isinstance(types, Set):
        types = tuple(types)
    # If this collection is a tuple *AND* the caller failed to guarantee this
    # tuple to be duplicate-free, coerce this tuple into (in order):
    # * A set, thus ignoring duplicates and ordering.
    # * Back into a duplicate-free tuple.
    elif isinstance(types, tuple) and not is_unique:
        types = tuple(set(types))
    # In either case, this collection is now guaranteed to be a tuple
    # containing only duplicate-free classes.
    assert isinstance(types, tuple), f'{exception_prefix}{repr(types)} not tuple.'

    # Name uniquely identifying this collection as a beartypistry key.
    tuple_types_name = f'{TYPISTRY_HINT_NAME_TUPLE_PREFIX}{hash(types)}'

    # If this tuple has *NOT* already been cached with the beartypistry
    # singleton, do so.
    if tuple_types_name not in bear_typistry:
        bear_typistry[tuple_types_name] = types
    # Else, this tuple has already been cached with the beartypistry singleton.
    # In this case, reuse the previously cached tuple.
    else:
        types = bear_typistry[tuple_types_name]

    # Return the name of a new parameter passing this tuple.
    return add_func_scope_attr(
        attr=types, func_scope=func_scope, exception_prefix=exception_prefix)

# ....................{ EXPRESSERS ~ type                  }....................
def express_func_scope_type_forwardref(
    # Mandatory parameters.
    forwardref: Pep484585ForwardRef,
    forwardrefs_class_basename: Optional[set],
    func_scope: LexicalScope,

    # Optional parameters.
    exception_prefix: str = 'Globally or locally scoped forward reference ',
) -> Tuple[str, Optional[set]]:
    '''
    Express the passed :pep:`484`- or :pep:`585`-compliant **forward reference**
    (i.e., fully-qualified or unqualified name of an arbitrary class that
    typically has yet to be declared) as a Python expression evaluating to this
    forward reference when accessed via the beartypistry singleton added as a
    new key-value pair of the passed dictionary, whose key is the string
    :attr:`beartype._check.checkmagic.ARG_NAME_TYPISTRY` and whose value is the
    beartypistry singleton.

    Parameters
    ----------
    forwardref : Pep484585ForwardRef
        Forward reference to be expressed relative to this scope.
    forwardrefs_class_basename : Optional[set]
        Set of all existing **relative forward references** (i.e., unqualified
        basenames of all types referred to by all relative forward references
        relative to this scope) if any *or* :data:`None` otherwise (i.e., if no
        relative forward references have been expressed relative to this scope).
    func_scope : LexicalScope
        Local or global scope to add this forward reference to.
    exception_prefix : str, optional
        Human-readable substring describing this forward reference in exception
        messages. Defaults to a reasonably sane string.

    Returns
    -------
    Tuple[str, Optional[set]]
        2-tuple ``(forwardref_expr, forwardrefs_class_basename)``, where:

        * ``forwardref_expr`` is the Python expression evaluating to this
          forward reference when accessed via the beartypistry singleton added
          to this scope.
        * ``forwardrefs_class_basename`` is either:

          * If this forward reference is a fully-qualified classname, the
            passed ``forwardrefs_class_basename`` set as is.
          * If this forward reference is an unqualified classname, either:

            * If the passed ``forwardrefs_class_basename`` set is *not*
              :data:`None`, this set with this classname added to it.
            * Else, a new set containing only this classname.

    Raises
    ------
    BeartypeDecorHintForwardRefException
        If this forward reference is *not* actually a forward reference.
    '''
    assert isinstance(func_scope, dict), f'{repr(func_scope)} not dictionary.'
    assert isinstance(forwardrefs_class_basename, NoneTypeOr[set]), (
        f'{repr(forwardrefs_class_basename)} neither set nor "None".')

    # If this object is *NOT* a forward reference, raise an exception.
    die_unless_hint_pep484585_ref(
        hint=forwardref, exception_prefix=exception_prefix)
    # Else, this object is a forward reference.

    # Fully-qualified or unqualified classname referred to by this reference.
    forwardref_classname = get_hint_pep484585_ref_name(forwardref)

    # If this classname contains one or more "." characters, this classname is
    # fully-qualified. In this case...
    if '.' in forwardref_classname:
        #FIXME: Unsafe. Encapsulate this operation in a new
        #add_func_scope_beartypistry() function validating that either:
        #* "ARG_NAME_TYPISTRY" has *NOT* already been added to this scope.
        #* "ARG_NAME_TYPISTRY" has already been added to this scope and its
        #  value is exactly the "bear_typistry" singleton.
        #To do so, we might consider simply generalizing the existing
        #add_func_scope_attr() function to optionally accept a new optional
        #"attr_name" parameter. When passed, that function should use that
        #string as the passed attribute's name rather than internally
        #generating its own non-human-readable attribute name.
        #FIXME: Actually, this now seems fine. We do this literally everywhere.
        #Let's probably just delete these "FIXME:" comments, please. *sigh*

        # Add the beartypistry singleton as a private "__beartypistry"
        # attribute to this scope.
        func_scope[ARG_NAME_TYPISTRY] = bear_typistry

        # Python expression evaluating to this class when accessed via this
        # private "__beartypistry" attribute.
        forwardref_expr = get_hint_forwardref_code(forwardref_classname)
    # Else, this classname is unqualified. In this case...
    else:
        # If this set of unqualified classnames referred to by all relative
        # forward references has yet to be instantiated, do so.
        if forwardrefs_class_basename is None:
            forwardrefs_class_basename = set()
        # In any case, this set now exists.

        # Add this unqualified classname to this set.
        forwardrefs_class_basename.add(forwardref_classname)

        # Placeholder substring to be replaced by the caller with a Python
        # expression evaluating to this unqualified classname canonicalized
        # relative to the module declaring the currently decorated callable
        # when accessed via the private "__beartypistry" parameter.
        forwardref_expr = (
            f'{CODE_HINT_REF_TYPE_BASENAME_PLACEHOLDER_PREFIX}'
            f'{forwardref_classname}'
            f'{CODE_HINT_REF_TYPE_BASENAME_PLACEHOLDER_SUFFIX}'
        )

    # Return a 2-tuple of this expression and set of unqualified classnames.
    return forwardref_expr, forwardrefs_class_basename
