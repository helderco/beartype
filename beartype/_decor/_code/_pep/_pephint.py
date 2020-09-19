#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2020 Cecil Curry.
# See "LICENSE" for further details.

'''
**Beartype decorator PEP-compliant type-checking graph-based code generator.**

This private submodule dynamically generates pure-Python code type-checking
arbitrary **PEP-compliant type hints** (i.e., :mod:`beartype`-agnostic
annotations compliant with annotation-centric PEPs) of the decorated callable
with a breadth-first search over the abstract graph of nested objects reachable
from the subscripted arguments of these hints.

This private submodule is *not* intended for importation by downstream callers.
'''

# ....................{ TODO                              }....................
#FIXME: We require two codepaths in the breadth-first search implemented by the
#pep_code_check_hint() function for each supported "typing" attribute,
#especially when we begin generating code type-checking container types:
#* If "IS_PYTHON_AT_LEAST_3_8", generate optimal code leveraging ":=" to
#  localize lengths, indices, and piths to avoid recomputing the same data over
#  and over again.
#* Else, generate suboptimal code sadly recomputing the same data over and over
#  again.
#
#Ergo, under Python <3.8, the code generated to test containers in particular
#is going to be suboptimally inefficient. There's no sane way around that.
#Fortunately, Python >=3.8 is the inevitable future, so this issue will
#naturally resolve itself over time. *shrug*
#FIXME: This would seem to be substantially easier than previously expected.
#For standard sequences, for example, we want to conditionally redefine in the
#body of the "if hint_child not in HINTS_IGNORABLE:" block the local
#"pith_curr_expr" variable prefixed by a dynamically uniquified string
#resembling "__beartype_pith_{N} := " (where "N" is a strictly positive integer
#trivially generated with a simple local integer counter variable initialized
#to 1 rather than a slower thread-safe "itertools.counter" object) if and only
#if all of the following constraints hold:
#* Python >= 3.8.
#* "hints_meta_index_curr != 0" (i.e., this is *NOT* the root hint and thus the
#  root pith). We want to exclude the root pith, which is already
#  unconditionally localized to "__beartype_pith_0" and thus does *NOT* require
#  re-localization with assignment expressions.
#* One or more subscripted arguments (i.e., child hints) of the currently
#  visited parent hint are PEP-compliant type hints. If all child hints of this
#  parent hint are simple types (e.g., "int", "str"), then this parent hint is
#  a leaf node. The whole point of using assignment expressions here is to
#  eliminate repeated computations in complex child hints. Ergo, a parent hint
#  with no complex child hints that would otherwise compute something does
#  *NOT* require localization of the current pith with assignment expressions.
#
#  This is the only non-trivial constraint to decide -- but it's still not
#  terribly arduous, especially for "typing" attributes constrained to single
#  arguments like "typing.List". "typing.Union" will require a bit of thought.
#
#If these constraints hold, we want to do something resembling:
#    pith_counter += 1
#    pith_curr_expr = (
#        '__beartype_pith_' + pith_counter + ' := ' + pith_curr_expr)
#FIXME: Right. So, the constraints given above absolutely apply, but the code
#really doesn't. The core issue is that we need to separate the LHS from the
#RHS of the assignment expression. Basically:
#* "pith_curr_expr" *MUST* be the LHS of the assignment expression, which
#  means that "pith_curr_expr" should be assigned *BEFORE* being passed to
#  child hints via "hint_child_meta" as follows:
#    pith_counter += 1
#    pith_curr_full_expr = pith_curr_expr
#    pith_curr_expr = '__beartype_pith_' + pith_counter
#  Note that we preserve the full current pith expression to a new
#  "pith_curr_full_expr" local variable, enabling us to subsequently format
#  that variable into snippets to assign that to "pith_curr_expr" via an
#  assignment expression.
#* The type-checking snippet for this "typing" attribute should conditionally
#  embed an assignment expression as a unique test guaranteed to *ALWAYS*
#  succeed whose sole purpose is to perform that assignment: e.g.,
#      PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_ASSIGN_EXPR = '''(
#      {indent_curr}    ({pith_curr_expr} := {pith_curr_full_expr}) is not __beartypistry and
#      {indent_curr}    isinstance({pith_curr_expr}, {hint_curr_expr}) and
#      {indent_curr}    {hint_child_placeholder} if {pith_curr_expr} else True
#      {indent_curr})'''
#  Since *NO* passed parameter or return value will ever be the private
#  "bear_typistry" singleton, the above assignment expression necessarily both
#  performs its assignment *AND* succeeds. So, that's nice.
#  Alternately, we could compact that into a single statement and thus avoid
#  the somewhat shady test against "bear_typistry" as follows:
#      PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_ASSIGN_EXPR = '''(
#      {indent_curr}    isinstance({pith_curr_expr} := {pith_curr_full_expr}, {hint_curr_expr}) and
#      {indent_curr}    {hint_child_placeholder} if {pith_curr_expr} else True
#      {indent_curr})'''
#  Note that we probably do require a separate assignment-specific snippet
#  entirely rather than somehow dynamically reformatting a single uniform
#  snippet based on the current constraints to embed an assignment expression,
#  due to divergent differences between the assigning and non-assigning
#  variants of each snippet. Note also that we will *ALWAYS* need to maintain
#  these two variants (even when dropping Python < 3.8 support), as the
#  non-assigning variant will still be required for both the root hint and all
#  leaf hints.
#  For that reason, it might be more disambiguous to name the above variants:
#  * "PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_LEVEL_MIDDLE", containing an
#    assignment expression.
#  * "PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_LEVEL_ROOT_OR_LEAF", containing no
#    assignment expression.
#  Actually, that's *NOT* necessarily the case. If we instead replace *ONLY*
#  the first instance of "{pith_curr_expr}" with "{pith_curr_first_expr}" in
#  any type-checking snippet, we can then conditionally replace
#  "{pith_curr_first_expr}" with either:
#  * If performing an assignment expression, then:
#      pith_curr_first_expr=pith_curr_expr + ':=' + pith_curr_full_expr
#  * Else:
#      pith_curr_first_expr=pith_curr_expr
#  Right. That clearly seems like the sane approach here. For example, the
#  standard sequence would then resemble:
#      PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD = '''(
#      {indent_curr}    isinstance({pith_curr_first_expr}, {hint_curr_expr}) and
#      {indent_curr}    {hint_child_placeholder} if {pith_curr_expr} else True
#      {indent_curr})'''
#  Sweetly succinct, eh?
#
#And... that's it, actually. This appears to be surprisingly trivial and
#efficient to generate code for, which is quite nice. Yay!
#FIXME: Note that "typing.Union" should require *NO* changes whatsoever, as
#unions unconditionally preserve the current pith -- unlike, say,
#"typing.List", which unconditionally changes the current pith. Also nice!

#FIXME: Significant optimizations still remain... when we have sufficient time.
#Notably, we can replace most existing usage of the generic private
#"__beartypistry" parameter unconditionally passed to all wrapper functions
#with specific private "__beartype_hint_{beartypistry_key}" parameters
#conditionally passed to each individual wrapper function, where:
#* "{beartypistry_key}" signifies an existing string key of the "bear_typistry"
#  singleton dictionary munged so as to produce a valid Python identifier.
#  Notably:
#  * Rather than use the fully-qualified names of types as we currently do,
#    we'll instead need to use their hashes. Why? Because Python identifiers
#    accept a sufficiently small set of permissible characters that there is
#    *NO* character we could possibly globally replace all "." characters in a
#    fully-qualified classname with to produce a disambiguous Python
#    identifier. Consider, for example, the two distinct classnames
#    "muh_package.muh_module.MuhClass" and
#    "muh_package_muh_module.MuhClass". Replacing "." characters with "_"
#    characters in both would produce the same munged Python identifier
#    "muh_package_muh_module_MuhClass" -- an ambiguous collision. Ergo, hashes.
#  * Hashes appear to be both negative and positive. So, we'll probably need to
#    replace "-" substrings prefixing "str(hash(hint))" output with something
#    sane complying with Python identifiers -- say, the "n" character. *shrug*
#* "__beartype_hint_{beartypistry_key}" signifies a parameter name whose value
#  defaults to either a type or tuple of types required by this wrapper
#  function.
#
#For example, if a function internally requires a "muh_package.MuhClass" class,
#we would then generate wrapper functions resembling:
#
#    def muh_wrapper(
#        *args,
#        __beartype_func=__beartype_func,
#        __beartype_hint_24234234240=__beartype_hint_24234234240,
#    )
#
#...where "__beartype_hint_24234234240" would need to be defined within the
#locals() dictionary passed to the exec() builtin by the "beartype._decor.main"
#submodule to refer to the "muh_package.MuhClass" class: e.g.,
#
#    # In "beartype._decor.main":
#    local_vars = {
#        __beartype_hint_24234234240: muh_package.MuhClass,
#    }
#
#Why is this so much more efficient than the current approach? Because lookups
#into large dictionaries inevitably have non-negligible constants, whereas
#exploiting default function parameters *IS LITERALLY INSTANTEOUS.* Why?
#Because Python actually stores function defaults in a tuple at function
#declaration time, thus minimizing both space and time costs: e.g.,
#    # It doesn't get faster than this, folks.
#    >>> def defjam(hmm, yum='Yum!', oko='Kek!'): pass
#    >>> defjam.__defaults__
#    ('Yum!', 'Kek!')
#
#Clearly, we'll need to carefully consider how we might efficiently percolate
#that metadata up from this breadth-first traversal to that top-level module.
#Presumably, we'll want to add a new data structure to the "BeartypeData"
#object -- say, a new "BeartypeData.param_name_to_value" dictionary mapping
#private parameter names to values to be passed to the current wrapper.
#
#Note that we should still cache at least tuples in the "bear_typistry"
#singleton dictionary to reduce space consumption for different tuple objects
#containing the same types, but that we should no longer look those tuples up
#in that dictionary at runtime from within wrapper functions.

#FIXME: Note that there exist four possible approaches to random item selection
#for arbitrary containers depending on container type. Either the actual pith
#object (in descending order of desirability):
#* Satisfies "collections.abc.Sequence" (*NOTE: NOT* "typing.Sequence", as we
#  don't particularly care how the pith is type-hinted for this purpose), in
#  which case the above approach trivially applies.
#* Else is *NOT* a one-shot container (e.g., generator and... are there any
#  other one-shot container types?) and is *NOT* slotted (i.e., has no
#  "__slots__" attribute), then generalize the mapping-specific
#  _get_dict_nonempty_random_key() approach delineated below.
#* Else is *NOT* a one-shot container (e.g., generator and... are there any
#  other one-shot container types?) but is slotted (i.e., has a "__slots__"
#  attribute), then the best we can do is the trivial O(1) approach by
#  calling "{hint_child_pith} := next({hint_curr_pith})" to unconditionally
#  check the first item of this container. What you goin' do? *shrug* (Note
#  that we could try getting around this with a global cache of weak references
#  to iterators mapped on object ID, but... ain't nobody got time or interest
#  for that. Also, prolly plenty dangerous.)
#* Else is a one-shot container, in which case *DO ABSOLUTELY NUTHIN'.*
#FIXME: We should ultimately make this user-configurable (e.g., as a global
#configuration setting). Some users might simply prefer to *ALWAYS* look up a
#fixed 0-based index (e.g., "0", "-1"). For the moment, however, the above
#probably makes the most sense as a reasonably general-purpose default.

#FIXME: Note that randomly checking mapping (e.g., "dict") keys and/or values
#will be non-trivial, as there exists no out-of-the-box O(1) approach in either
#the general case or the specific case of a "dict". Actually, there does -- but
#we'll need to either internally or externally maintain one dict.items()
#iterator for each passed mapping. We should probably investigate the space
#costs of that *BEFORE* doing so. Assuming minimal costs, one solution under
#Python >= 3.8 might resemble:
#* Define a new _get_dict_random_key() function resembling:
#      def _get_dict_nonempty_random_key(mapping: MappingType) -> object:
#          '''
#          Caveats
#          ----------
#          **This mapping is assumed to be non-empty.** If this is *not* the
#          case, this function raises a :class:`StopIteration` exception.
#          '''
#          items_iter = getattr(mapping, '__beartype_items_iter', None)
#          if items_iter is None:
#              #FIXME: This should probably be a weak reference to prevent
#              #unwanted reference cycles and hence memory leaks.
#              #FIXME: We need to protect this both here and below with a
#              #"try: ... except Exception: ..." block, where the body of the
#              #"except Exception:" condition should probably just return
#              #"beartype._util.utilobject.SENTINEL", as the only type hints
#              #that would ever satisfy are type hints *ALL* objects satisfy
#              #(e.g., "Any", "object").
#              mapping.__beartype_items_iter = iter(mapping.items())
#          try:
#              return next(mapping.__beartype_items_iter)
#          # If we get to the end (i.e., the prior call to next() raises a
#          # "StopIteration" exception) *OR* anything else happens (i.e., the
#          # prior call to next() raises a "RuntimeError" exception due to the
#          # underlying mapping having since been externally mutated), just
#          # start over. :p
#          except Exception:
#              mapping.__beartype_items_iter = None
#
#              # We could also recursively call ourselves: e.g.,
#              #     return _get_dict_random_key(mapping)
#              # However, that would be both inefficient and dangerous.
#              mapping.__beartype_items_iter = iter(mapping.items())
#              return next(mapping.__beartype_items_iter)
#* In "beartype._decor._main":
#     import _get_dict_nonempty_random_key as __beartype_get_dict_nonempty_random_key
#* In code generated by this submodule, internally call that helper when
#  checking keys of non-empty mappings *THAT ARE UNSLOTTED* (for obvious
#  reasons) ala:
#  (
#     {hint_curr_pith} and
#     not hasattr({hint_curr_pith}, '__slots__') and
#     {!INSERT_CHILD_TEST_HERE@?(
#         {hint_child_pith} := __beartype_get_dict_nonempty_random_key({hint_curr_pith}))
#  )
#  Obviously not quite right, but gives one the general gist of the thing.
#
#We could get around the slots limitation by using an external LRU cache
#mapping from "dict" object ID to items iterator, and maybe that *IS* what we
#should do. Actually... *NO.* We absolutely should *NOT* do that sort of thing
#anywhere in the codebase, as doing so would guaranteeably induce memory leaks
#by preventing "dict" objects cached in that LRU from being garbage collected.
#
#Note that we basically can't do this under Python < 3.8, due to the lack of
#assignment expressions there. Since _get_dict_nonempty_random_key() returns a
#new random key each call, we can't repeatedly call that for each child pith
#and expect the same random key to be returned. So, Python >= 3.8 only. *shrug*
#
#Note that the above applies to both immutable mappings (i.e., objects
#satisfying "Mapping" but *NOT* "MutableMapping"), which is basically none of
#them, and mutable mappings. Why? Because we don't particularly care if the
#caller externally modifies the underlying mapping between type-checks, even
#though the result is the above call to "next(mapping.__beartype_items_iter)"
#raising a "RuntimeError". Who cares? Whenever an exception occurs, we just
#restart iteration over from the beginning and carry on. *GOOD 'NUFF.*
#FIXME: When time permits, we can augment the pretty lame approach by
#publishing our own "BeartypeDict" class that supports efficient random access
#of both keys and values. Note that:
#* The existing third-party "randomdict" package provides baseline logic that
#  *MIGHT* be useful in getting "BeartypeDict" off the ground. The issue with
#  "randomdict", however, is that it internally leverages a "list", which
#  probably then constrains key-value pair deletions on the exterior
#  "randomdict" object to an O(n) rather than O(1) operation, which is
#  absolutely unacceptable.
#* StackOverflow questions provide a number of solutions that appear to be
#  entirely O(1), but which require maintaining considerably more internal data
#  structures, which is also unacceptable (albeit less so), due to increased
#  space consumption that probably grows unacceptable fast and thus fails to
#  generally scale.
#* Since we don't control "typing", we'll also need to augment "BeartypeDict"
#  with a "__class_getitem__" dunder method (or whatever that is called) to
#  enable that class to be subscripted with "typing"-style types ala:
#     def muh_func(muh_mapping: BeartypeDict[str, int]) -> None: pass
#In short, we'll need to conduct considerably more research here.

#FIXME: Type-check instances of user-defined subclasses subclassing multiple
#"typing" pseudo-superclasses. While we currently do iterate over these
#superclasses properly in the breadth-first search implemented below, we
#currently do *NOT* generate sane code type-checking such instances against
#these superclasses and thus raise exceptions on detecting such subclasses.
#See the related "FIXME:" comment preceding this test below.:
#           elif len(hint_curr_attrs_to_args) > 2:

#FIXME: Type-check instances of types subclassing the "typing.Protocol"
#superclass decorated by the @runtime_checkable decorator, detectable at
#runtime by the existence of both "typing.Protocol" in their "__mro__" dunder
#attribute *AND* the protocol-specific private "_is_runtime_protocol" instance
#variable set to True.
#
#Specifically, refactor the codebase as follows to support protocols:
#
#* Define a new utilhintpeptest.is_hint_pep_protocol() tester returning True if
#  the passed object is a @runtime_checkable-decorated Protocol. See below for
#  the logic necessary to do so. This is non-trivial, as "Protocol" was only
#  introduced under Python >= 3.8 *BUT* various "typing" subclasses of a
#  private "_Protocol" superclass have been available since Python >= 3.5.
#* Define a new utilhinttest.is_hint_isinstanceable() tester returning True if
#  the passed object is a type that either:
#  * Is a non-"typing" type.
#  * Is a @runtime_checkable-decorated Protocol subclass.
#* Call the is_hint_isinstanceable() tester *BEFORE* the is_hint_pep() tester
#  everywhere in this codebase. Notably:
#  * Revise:
#    # ...this test...
#    elif isinstance(hint_curr, type):
#    # ...into this test.
#    elif is_hint_isinstanceable(hint_curr):
#  * Shift that test before the "if is_hint_pep(hint_curr):"
#    test above.
#  * Revise the above union-specific tests from:
#    # ...this logic...
#         # If this argument is PEP-compliant...
#         if is_hint_pep(hint_child):
#             # Filter this argument into the list of
#             # PEP-compliant arguments.
#             hint_childs_pep.append(hint_child)
#
#         # Else, this argument is PEP-noncompliant. In this
#         # case, filter this argument into the list of
#         # PEP-noncompliant arguments.
#         else:
#             hint_childs_nonpep.append(hint_child)
#
#    # ...into this logic.
#         # If this argument is an isinstance()-compatible
#         # type, filter this argument into the list of these
#         # types.
#         if is_hint_isinstanceable(hint_child):
#             hint_childs_nonpep.append(hint_child)
#         # Else, this argument is *NOT* an
#         # isinstance()-compatible type. In this case...
#         else:
#             # If this argument is *NOT* a PEP-compliant
#             # type hint, raise an exception.
#             die_unless_hint_pep(
#                 hint=hint_child, hint_label=???)
#             # Else, this argument is a PEP-compliant
#             # type hint.
#
#             # Filter this argument into the list of
#             # PEP-compliant arguments.
#             hint_childs_pep.append(hint_child)
#
#Note lastly that support for protocols conditionally depends on the current
#Python version. Besically:
#
#* Under Python < 3.8, the following abstract base classes (ABCs) are standard
#  ABCs and thus trivially support isinstance() as is:
#  * typing.SupportsInt
#  * typing.SupportsFloat
#  * typing.SupportsComplex
#  * typing.SupportsBytes
#  * typing.SupportsAbs
#  * typing.SupportsRound
#  Note that "typing.Protocol" does *NOT* exist here. Ergo, the
#  is_hint_pep_protocol() tester should return True under Python < 3.8 only if
#  the passed hint is an instance of one of these six ABCs. This is essential,
#  as these instances would otherwise be treated as PEP-compliant type hints --
#  which they're not, really.
#* Under Python >= 3.8, the "typing.Protocol" superclass appears and all of the
#  above ABCs both subclass that *AND* are decorated by @runtime_checkable.
#  Lastly, a new "typing.SupportsIndex" ABC is introduced as well. So, we need
#  to check that the protocol-specific private "_is_runtime_protocol" instance
#  variable is set to True
#  for "Protocol" subclasses.
#FIXME: Note that the ProtocolMeta.__subclasshook__() dunder method
#implementation is insanely inefficient in a way that only "typing" authors
#could have written. Ideally, rather than naively calling isinstance() on
#instances of core "typing.Protocol" subclasses defined by the "typing" module
#itself (e.g., "typing.SupportsInt"), we would instead generate efficient code
#directly type-checking that those instances define the requisite attributes.
#Note, however, that the typing.Protocol.__init_subclass__._proto_hook()
#implementing structural subtyping checks is sufficiently non-trivial that we
#*REALLY* don't want to get into that for now.

#FIXME: Type-check "typing.NoReturn", too. Note that whether a callable returns
#"None" or not is *NOT* a sufficient condition to positively declare a function
#to return no value for hopefully obvious reasons. Rather, we instead need to
#validate this condition entirely at decoration time by either:
#* Disassembling the decorated callable with the "dis" module and parsing the
#  returned bytecode assembly for the first "return" statement if any.
#* Constructing the abstract syntax tree (AST) for the decorated callable with
#  the "ast" module and parsing the returned AST for the first node marked as a
#  "return" statement if any.


#FIXME: Resolve PEP-compliant forward references as well. Note that doing so is
#highly non-trivial -- sufficiently so, in fact, that we probably want to do so
#elsewhere as cleverly documented in the "_pep563" submodule.

# ....................{ IMPORTS                           }....................
from beartype.roar import BeartypeDecorHintPepException
from beartype._decor._data import BeartypeData
from beartype._decor._typistry import (
    register_typistry_type,
    register_typistry_tuple,
)
from beartype._decor._code._codesnip import (
    CODE_INDENT_1, CODE_INDENT_2, CODE_INDENT_3)
from beartype._decor._code._pep._pepsnip import (
    PEP_CODE_CHECK_HINT_ROOT,
    PEP_CODE_CHECK_HINT_NONPEP_TYPE,
    PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD,
    PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_PITH_CHILD_EXPR,
    PEP_CODE_CHECK_HINT_UNION_PREFIX,
    PEP_CODE_CHECK_HINT_UNION_SUFFIX,
    PEP_CODE_CHECK_HINT_UNION_ARG_NONPEP,
    PEP_CODE_CHECK_HINT_UNION_ARG_PEP,
    PEP_CODE_PITH_ROOT_EXPR,
)
# from beartype._util.utilpy import IS_PYTHON_AT_LEAST_3_8
from beartype._util.hint.utilhintget import (
    get_hint_type_origin, get_hint_type_origin_or_none)
from beartype._util.hint.pep.utilhintpepdata import (
    TYPING_ATTR_TO_TYPE_ORIGIN,
    TYPING_ATTRS_SEQUENCE_STANDARD,
)
from beartype._util.hint.pep.utilhintpepget import (
    get_hint_pep_typing_attr)
from beartype._util.hint.pep.utilhintpeptest import (
    die_unless_hint_pep_supported,
    die_unless_hint_pep_typing_attr_supported,
    is_hint_pep,
)
from beartype._util.cache.utilcachecall import callable_cached
from beartype._util.cache.pool.utilcachepoollistfixed import (
    SIZE_BIG, FixedList, acquire_fixed_list, release_fixed_list)
from beartype._util.cache.utilcacheerror import (
    EXCEPTION_CACHED_PLACEHOLDER)
from beartype._util.hint.utilhintdata import HINTS_IGNORABLE
from itertools import count
from typing import (
    Union,
)

# See the "beartype.__init__" submodule for further commentary.
__all__ = ['STAR_IMPORTS_CONSIDERED_HARMFUL']

# ....................{ CONSTANTS ~ hint : meta           }....................
# Iterator yielding the next integer incrementation starting at 0, to be safely
# deleted *AFTER* defining the following 0-based indices via this iterator.
__hint_meta_index_counter = count(start=0, step=1)


_HINT_META_INDEX_HINT = next(__hint_meta_index_counter)
'''
0-based index into each fixed list of hint metadata providing the currently
visited hint.
'''


_HINT_META_INDEX_PLACEHOLDER = next(__hint_meta_index_counter)
'''
0-based index into each fixed list of hint metadata providing the **current
placeholder type-checking substring** (i.e., placeholder to be globally
replaced by a Python code snippet type-checking the current pith expression
against the hint described by this metadata on visiting that hint).

This substring provides indirection enabling the currently visited parent hint
to defer and delegate the generation of code type-checking each child argument
of that hint to the later time at which that child argument is visited.

Example
----------
For example, the :func:`pep_code_check_hint` function might generate
intermediary code resembling the following on visiting the :data:`Union` parent
of a ``Union[int, str]`` object *before* visiting either the :class:`int` or
:class:`str` children of that object:

    if not (
        @{0}! or
        @{1}!
    ):
        raise __beartype_raise_pep_call_exception(
            func=__beartype_func,
            param_or_return_name=$%PITH_ROOT_NAME/~,
            param_or_return_value=__beartype_pith_root,
        )

Note the unique substrings "@{0}!" and "@{1}!" in that code, which that
function iteratively replaces with code type-checking each of the child
arguments of that :data:`Union` parent (i.e., :class:`int`, :class:`str`). The
final code memoized by that function might then resemble:

    if not (
        isinstance(__beartype_pith_root, int) or
        isinstance(__beartype_pith_root, str)
    ):
        raise __beartype_raise_pep_call_exception(
            func=__beartype_func,
            param_or_return_name=$%PITH_ROOT_NAME/~,
            param_or_return_value=__beartype_pith_root,
        )
'''


_HINT_META_INDEX_PITH_EXPR = next(__hint_meta_index_counter)
'''
0-based index into each fixed list of hint metadata providing the **current
pith expression** (i.e., Python code snippet evaluating to the current possibly
nested object of the passed parameter or return value to be type-checked
against the currently visited hint).
'''


_HINT_META_INDEX_INDENT = next(__hint_meta_index_counter)
'''
0-based index into each fixed list of hint metadata providing **current
indentation** (i.e., Python code snippet expanding to the current level of
indentation appropriate for the currently visited hint).
'''


_HINT_META_SIZE = next(__hint_meta_index_counter)
'''
Length to constrain **hint metadata** (i.e., fixed lists efficiently
masquerading as tuples of metadata describing the currently visited hint,
defined by the previously visited parent hint as a means of efficiently sharing
metadata common to all children of that hint) to.
'''

# Delete the above counter for safety and sanity in equal measure.
del __hint_meta_index_counter

# ....................{ CODERS                            }....................
@callable_cached
def pep_code_check_hint(data: BeartypeData, hint: object) -> str:
    '''
    Python code type-checking the previously localized parameter or return
    value annotated by the passed PEP-compliant type hint against this hint of
    the decorated callable.

    This code generator is memoized for efficiency.

    Caveats
    ----------
    **This function intentionally accepts no** ``hint_label`` **parameter.**
    Why? Since that parameter is typically specific to the caller, accepting
    that parameter would effectively prevent this code generator from memoizing
    the passed hint with the returned code, which would rather defeat the
    point. Instead, this function only:

    * Returns generic non-working code containing the placeholder
      :attr:`beartype._decor._code._pep.pepcode.PITH_ROOT_NAME_PLACEHOLDER_STR`
      substring that the caller is required to globally replace by the name of
      the current parameter *or* ``return`` for return values (e.g., by calling
      the builtin :meth:`str.replace` method) to generate the desired
      non-generic working code type-checking that parameter or return value.
    * Raises generic non-human-readable exceptions containing the placeholder
      :attr:`beartype._util.cache.utilcacheerror.EXCEPTION_CACHED_PLACEHOLDER`
      substring that the caller is required to explicitly catch and raise
      non-generic human-readable exceptions from by calling the
      :func:`beartype._util.cache.utilcacheerror.reraise_exception_cached`
      function.

    Parameters
    ----------
    data : BeartypeData
        Decorated callable to be type-checked.
    hint : object
        PEP-compliant type hint to be type-checked.

    Returns
    ----------
    str
        Python code type-checking the previously localized parameter or return
        value against this hint.

    Raises
    ----------
    BeartypeDecorHintPepException
        If this object is *not* a PEP-compliant type hint.
    BeartypeDecorHintPepUnsupportedException
        If this object is a PEP-compliant type hint but is currently
        unsupported by the :func:`beartype.beartype` decorator.
    '''
    # Note this hint need *NOT* be validated as a PEP-compliant type hint
    # (e.g., by explicitly calling the die_unless_hint_pep_supported()
    # function). By design, the caller already guarantees this to be the case.
    assert data.__class__ is BeartypeData, (
        '{!r} not @beartype data.'.format(data))

    # ..................{ ATTRIBUTES                        }..................
    # Localize attributes of this dataclass for negligible efficiency gains.
    # Notably, alias:
    #
    # * The generic "data.set_a" set as the readable "hint_childs_nonpep",
    #   accessed below as the set of all PEP-noncompliant types listed by the
    #   currently visited hint.
    # * The generic "data.set_b" set as the readable "hint_childs_pep",
    #   accessed below as the set of all PEP-compliant types listed by the
    #   currently visited hint.
    get_next_pep_hint_placeholder = data.get_next_pep_hint_placeholder
    hint_childs_nonpep = data.set_a
    hint_childs_pep    = data.set_b
    hint_childs_nonpep_add = hint_childs_nonpep.add
    hint_childs_pep_add    = hint_childs_pep.add

    # Localize attributes of the "_pepsnip" submodule for similar gains.
    PEP_CODE_CHECK_HINT_NONPEP_TYPE_format = (
        PEP_CODE_CHECK_HINT_NONPEP_TYPE.format)
    PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_format = (
        PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD.format)
    PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_PITH_CHILD_EXPR_format = (
        PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_PITH_CHILD_EXPR.format)
    PEP_CODE_CHECK_HINT_UNION_ARG_PEP_format = (
        PEP_CODE_CHECK_HINT_UNION_ARG_PEP.format)
    PEP_CODE_CHECK_HINT_UNION_ARG_NONPEP_format = (
        PEP_CODE_CHECK_HINT_UNION_ARG_NONPEP.format)

    # ..................{ HINT ~ root                       }..................
    # Top-level hint relocalized for disambiguity. For the same reason, delete
    # the passed parameter whose name is ambiguous within the context of this
    # code generator.
    hint_root = hint
    del hint

    #FIXME: Refactor to leverage f-strings after dropping Python 3.5 support,
    #which are the optimal means of performing string formatting.

    # Human-readable label describing the root hint in exception messages.
    hint_root_label = EXCEPTION_CACHED_PLACEHOLDER + ' ' + repr(hint_root)

    # ..................{ HINT ~ current                    }..................
    # Currently visited hint.
    hint_curr = None

    # Current argumentless typing attribute associated with this hint (e.g.,
    # "Union" if "hint_curr == Union[int, str]").
    hint_curr_attr = None

    # Python expression evaluating to an isinstance()-able class (e.g., origin
    # type) associated with the currently visited type hint if any.
    hint_curr_expr = None

    #FIXME: Excise us up.
    # Origin type (i.e., non-"typing" superclass suitable for shallowly
    # type-checking the current pith against the currently visited hint by
    # passing both to the isinstance() builtin) of this hint if this hint
    # originates from such a superclass.
    # hint_curr_type_origin = None

    # Placeholder string to be globally replaced in the Python code snippet to
    # be returned (i.e., "func_code") by a Python code snippet type-checking
    # the current pith expression (i.e., "pith_curr_expr") against the
    # currently visited hint (i.e., "hint_curr").
    hint_curr_placeholder = None

    # Python code snippet evaluating to the current (possibly nested) object of
    # the passed parameter or return value to be type-checked against the
    # currently visited hint.
    pith_curr_expr = None

    # Python code snippet expanding to the current level of indentation
    # appropriate for the currently visited hint.
    indent_curr = CODE_INDENT_2

    # ..................{ HINT ~ child                      }..................
    # Current tuple of all subscripted arguments defined on this hint (e.g.,
    # "(int, str)" if "hint_curr == Union[int, str]").
    hint_childs = None

    # Currently iterated subscripted argument defined on this hint.
    hint_child = None

    #FIXME: Excise us up.
    # Current argumentless typing attribute associated with this hint (e.g.,
    # "Union" if "hint_child == Union[int, str]").
    # hint_child_attr = None

    # Human-readable label prefixing the representations of child hints of this
    # root hint in exception messages.
    #
    # Note that this label intentionally only describes the root and currently
    # iterated child hints rather than the root hint, the currently iterated
    # child hint, and all interim child hints leading from the former to the
    # latter. The latter approach would be non-human-readable and insane.
    hint_child_label = hint_root_label + ' child'

    # Placeholder string to be globally replaced in the Python code snippet to
    # be returned (i.e., "func_code") by a Python code snippet type-checking
    # the child pith expression (i.e., "pith_child_expr") against the currently
    # iterated child hint (i.e., "hint_child").
    hint_child_placeholder = get_next_pep_hint_placeholder()

    #FIXME: Excise us up.
    # Python expression evaluating to the value of the currently iterated child
    # hint of the currently visited parent hint.
    # hint_child_expr = None

    # Origin type (i.e., non-"typing" superclass suitable for shallowly
    # type-checking the current pith against the currently visited hint by
    # passing both to the isinstance() builtin) of the currently iterated child
    # hint of the currently visited parent hint.
    hint_child_type_origin = None

    #FIXME: Excise us up.
    # Python code snippet evaluating to the current (possibly nested) object of
    # the passed parameter or return value to be type-checked against the
    # currently iterated child hint.
    #pith_child_expr = None

    # Python code snippet expanding to the current level of indentation
    # appropriate for the currently iterated child hint.
    indent_child = None

    # ..................{ METADATA                          }..................
    # Fixed list of metadata describing the root hint.
    hint_root_meta = acquire_fixed_list(_HINT_META_SIZE)
    hint_root_meta[_HINT_META_INDEX_HINT] = hint_root
    hint_root_meta[_HINT_META_INDEX_PLACEHOLDER] = hint_child_placeholder
    hint_root_meta[_HINT_META_INDEX_PITH_EXPR] = PEP_CODE_PITH_ROOT_EXPR
    hint_root_meta[_HINT_META_INDEX_INDENT] = indent_curr

    # Fixed list of metadata describing the currently visited hint, appended by
    # the previously visited parent hint to the "hints_meta" stack.
    hint_curr_meta = None

    # Fixed list of metadata describing a child hint to be subsequently
    # visited, appended by the currently visited parent hint to that stack.
    hint_child_meta = None

    # Fixed list of all metadata describing all visitable hints currently
    # discovered by the breadth-first search below, seeded with metadata
    # describing the root hint.
    #
    # Since "SIZE_BIG" is guaranteed to be substantially larger than 1, this
    # assignment is quite guaranteed to be safe. (Quite. Very. Mostly. Kinda.)
    hints_meta = acquire_fixed_list(SIZE_BIG)
    hints_meta[0] = hint_root_meta

    # 0-based index of metadata describing the currently visited hint in the
    # "hints_meta" list.
    hints_meta_index_curr = 0

    # 0-based index of metadata describing the last visitable hint in the
    # "hints_meta" list.
    hints_meta_index_last = 0

    # ..................{ CODE                              }..................
    #FIXME: Refactor to leverage f-strings after dropping Python 3.5 support,
    #which are the optimal means of performing string formatting.

    # Python code snippet type-checking the root pith against the root hint,
    # localized separately from the "func_code" snippet to enable this function
    # to validate this code to be valid *BEFORE* returning this code.
    func_root_code = PEP_CODE_CHECK_HINT_ROOT.format(
        hint_child_placeholder=hint_child_placeholder)

    # Python code snippet type-checking the current pith against the currently
    # visited hint (to be appended to the "func_code" string).
    func_curr_code = None

    # Python code snippet to be returned, seeded with a placeholder to be
    # subsequently replaced on the first iteration of the breadth-first search
    # performed below with a snippet type-checking the root pith against the
    # root hint.
    func_code = func_root_code

    # ..................{ SEARCH                            }..................
    # While the 0-based index of metadata describing the next visited hint in
    # the "hints_meta" list does *NOT* exceed that describing the last
    # visitable hint in this list, there remains at least one hint to be
    # visited in the breadth-first search performed by this iteration.
    while hints_meta_index_curr <= hints_meta_index_last:
        # Metadata describing the currently visited hint.
        hint_curr_meta = hints_meta[hints_meta_index_curr]
        assert hint_curr_meta.__class__ is FixedList, (
            'Current hint metadata {!r} at index {!r} '
            'not a fixed list.'.format(hint_curr_meta, hints_meta_index_curr))

        # Localize metadatum for both efficiency and f-string purposes.
        hint_curr             = hint_curr_meta[_HINT_META_INDEX_HINT]
        hint_curr_placeholder = hint_curr_meta[_HINT_META_INDEX_PLACEHOLDER]
        pith_curr_expr        = hint_curr_meta[_HINT_META_INDEX_PITH_EXPR]
        indent_curr           = hint_curr_meta[_HINT_META_INDEX_INDENT]

        #FIXME: Comment this sanity check out after we're sufficiently
        #convinced this algorithm behaves as expected. While useful, this check
        #requires a linear search over the entire code and is thus costly.
        # assert hint_curr_placeholder in func_code, (
        #     '{} {!r} placeholder {} not found in wrapper body:\n{}'.format(
        #         hint_child_label, hint, hint_curr_placeholder, func_code))

        # If this hint is PEP-compliant...
        if is_hint_pep(hint_curr):
            # If this hint is currently unsupported, raise an exception.
            #
            # Note the human-readable label prefixing the representations of
            # child PEP-compliant type hints is unconditionally passed. Since
            # the root hint has already been validated to be supported by
            # the above call to the same function, this call is guaranteed to
            # *NEVER* raise an exception for that hint.
            die_unless_hint_pep_supported(
                hint=hint_curr, hint_label=hint_child_label)
            # Else, this hint is supported.

            # Assert that this hint is unignorable. Iteration below generating
            # code for child hints of the current parent hint is *REQUIRED* to
            # explicitly ignore ignorable child hints. Since the caller has
            # explicitly ignored ignorable root hints, these two guarantees
            # together ensure that all hints visited by this breadth-first
            # search *SHOULD* be unignorable. Naturally, we validate that here.
            assert hint_curr not in HINTS_IGNORABLE, (
                '{} {!r} ignorable.'.format(hint_child_label, hint_curr))

            # Argumentless "typing" attribute uniquely identifying this hint.
            hint_curr_attr = get_hint_pep_typing_attr(hint_curr)

            # If this attribute is currently unsupported, raise an exception.
            #
            # Note the human-readable label prefixing the representations of
            # child PEP-compliant type hints is unconditionally passed. Since
            # the root hint has already been validated to be supported by the
            # above call to the die_unless_hint_pep_supported() function, this
            # call is guaranteed to *NEVER* raise exceptions for the root hint.
            die_unless_hint_pep_typing_attr_supported(
                hint=hint_curr_attr, hint_label=hint_child_label)
            # Else, this attribute is supported.

            # Python code snippet expanding to the current level of indentation
            # appropriate for the currently iterated child hint.
            #
            # Note that this is almost always but technically *NOT* always
            # required below by logic generating code type-checking the
            # currently visited parent hint. Naturally, unconditionally setting
            # this string here trivially optimizes the common case.
            indent_child = indent_curr + CODE_INDENT_1

            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # NOTE: Whenever adding support for (i.e., when generating code
            # type-checking) a new "typing" attribute below, similar support
            # for that attribute *MUST* also be added to the parallel:
            # * "beartype._util.hint.pep.utilhintpepcall" submodule (i.e.,
            #   raising exceptions when the current pith fails this check).
            # * "beartype._util.hint.pep.utilhintpepdata.TYPING_ATTRS_SUPPORTED"
            #   frozen set of all supported argumentless "typing" attributes.
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            # Switch on (as in, pretend Python provides a "switch" statement)
            # this attribute to decide which type of code to generate to
            # type-check the current pith against the current hint.
            #
            # This decision is intentionally implemented as a linear series of
            # tests ordered in descending likelihood for efficiency. While
            # alternative implementations (that are more readily readable and
            # maintainable) do exist, these alternatives all appear to be
            # substantially less efficient.
            #
            # Consider the standard alternative of sequestering the body of
            # each test implemented below into either:
            #
            # * A discrete private function called by this function. This
            #   approach requires maintaining a global private dictionary
            #   mapping from each support argumentless typing attribute to
            #   the function generating code for that attribute: e.g.,
            #      def pep_code_check_union(...): ...
            #      _HINT_TYPING_ATTR_ARGLESS_TO_CODER = {
            #          typing.Union: pep_code_check_union,
            #      }
            #   Each iteration of this loop then looks up the function
            #   generating code for the current attribute from this dictionary
            #   and calls that function to do so. Function calls come with
            #   substantial overhead in Python, impacting performance more
            #   than the comparable linear series of tests implemented below.
            #   Additionally, these functions *MUST* mutate local variables of
            #   this function by some arcane means -- either:
            #   * Passing these locals to each such function, returning these
            #     locals from each such function, and assigning these return
            #     values to these locals in this function after each such call.
            #   * Passing a single composite fixed list of these locals to each
            #     such function, which then mutates these locals in-place,
            #     which then necessitates this function permanently store these
            #     locals in such a list rather than as local variables.
            # * A discrete closure of this function, which adequately resolves
            #   the aforementioned locality issue via the "nonlocal" keyword at
            #   a substantial up-front performance cost of redeclaring these
            #   closures on each invocation of this function.

            # ..............{ UNIONS                            }..............
            # If this hint is a union...
            #
            # Note that, as unions are non-physical abstractions of physical
            # types, unions themselves are *NOT* type-checked; only the
            # subscripted arguments of unions are type-checked. This differs
            # from "typing" pseudo-containers like "List[int]", in which both
            # the parent "List" and child "int" types represent physical types
            # to be type-checked. Ergo, unions themselves impose no narrowing
            # of the current pith expression.
            if hint_curr_attr is Union:
                # Tuple of all subscripted arguments defining this union,
                # localized for both minor efficiency and major readability.
                #
                # Note that the "__args__" dunder attribute is *NOT* generally
                # guaranteed to exist for arbitrary PEP-compliant type hints
                # but is specifically guaranteed to exist for all unions other
                # than the argumentless "typing.Union" attribute, which
                # semantically reduces to "typing.Union[typing.Any]", which is
                # thus ignored above and thus guaranteed *NOT* to be visitable
                # here. Ergo, this attribute is guaranteed to exist here.
                hint_childs = hint_curr.__args__

                # Assert this union is unsubscripted. Note this should *NEVER*
                # happen, as:
                #
                # * The unsubscripted "typing.Union" object is explicitly
                #   listed in the "HINTS_IGNORABLE" set and should thus have
                #   already been ignored when present.
                # * The "typing" module explicitly prohibits empty
                #   subscription: e.g.,
                #       >>> typing.Union[]
                #       SyntaxError: invalid syntax
                #       >>> typing.Union[()]
                #       TypeError: Cannot take a Union of no types.
                assert hint_childs, (
                    '{} {!r} unsubscripted.'.format(hint_child_label, hint))
                # Else, this union is subscripted by two or more arguments. Why
                # two rather than one? Because the "typing" module reduces
                # unions of one argument to that argument: e.g.,
                #     >>> import typing
                #     >>> typing.Union[int]
                #     int

                # Clear the sets of all PEP-compliant and -noncompliant types
                # listed as subscripted arguments of this union. Since these
                # types require fundamentally different forms of type-checking,
                # prefiltering arguments into these sets *BEFORE* generating
                # code type-checking these arguments improves both efficiency
                # and maintainability below.
                hint_childs_nonpep.clear()
                hint_childs_pep.clear()

                # For each subscripted argument of this union...
                for hint_child in hint_childs:
                    # If this argument is unignorable...
                    if hint_child not in HINTS_IGNORABLE:
                        # If this argument is PEP-compliant...
                        if is_hint_pep(hint_child):
                            # Filter this argument into the set of
                            # PEP-compliant arguments.
                            hint_childs_pep_add(hint_child)

                            # Origin type of the argumentless "typing"
                            # attribute associated with this argument if any
                            # *OR* "None" otherwise.
                            hint_child_type_origin = (
                                get_hint_type_origin_or_none(
                                    get_hint_pep_typing_attr(
                                        hint_child)))

                            # If this argument originates from such a type,
                            # filter this argument into the set of
                            # PEP-noncompliant arguments as well.
                            #
                            # Note that this is purely optional, but optimizes
                            # the common case of unions of containers. Given a
                            # PEP-compliant hint "Union[int, List[str]]", this
                            # case generates code initially testing whether the
                            # current pith satisfies "isinstance(int, list)"
                            # *BEFORE* subsequently testing whether this pith
                            # deeply satisfies the nested hint "List[str]" when
                            # this pith is a list. This is good, eh?
                            # print('Testing union PEP hint_child: {!r}'.format(hint_child))
                            if hint_child_type_origin is not None:
                                # print('Adding union hint_child_type_origin: {!r}'.format(hint_child_type_origin))
                                hint_childs_nonpep_add(
                                    hint_child_type_origin)
                        # Else, this argument is PEP-noncompliant. In this
                        # case, filter this argument into the list of
                        # PEP-noncompliant arguments.
                        else:
                            hint_childs_nonpep_add(hint_child)
                    # Else, this argument is ignorable.
                # All subscripted arguments of this union are now prefiltered
                # into the list of PEP-compliant or -noncompliant arguments.

                # Initialize the code type-checking the current pith against
                # these arguments to the substring prefixing all such code.
                func_curr_code = PEP_CODE_CHECK_HINT_UNION_PREFIX

                # If this union is subscripted by one or more PEP-noncompliant
                # arguments, generate efficient code type-checking these
                # arguments before less efficient code type-checking any
                # PEP-compliant arguments subscripting this union.
                if hint_childs_nonpep:
                    #FIXME: Refactor to leverage f-strings after dropping
                    #Python 3.5 support, which are the optimal means of
                    #performing string formatting.

                    # Append code type-checking these arguments.
                    #
                    # Defer formatting the "indent_curr" prefix into this code
                    # until below for efficiency.
                    func_curr_code += (
                        PEP_CODE_CHECK_HINT_UNION_ARG_NONPEP_format(
                            pith_curr_expr=pith_curr_expr,
                            # Python expression evaluating to a tuple of these
                            # arguments when accessed via the private
                            # "__beartypistry" parameter.
                            #
                            # Note that we would ideally avoid coercing this
                            # set into a tuple when this set only contains one
                            # type by passing that type directly to the
                            # register_typistry_type() function. Sadly, the
                            # "set" class defines no convenient or efficient
                            # means of retrieving the only item of a 1-set.
                            # Indeed, the most efficient means of doing so is
                            # to iterate over that set and immediately break:
                            #     for first_item in muh_set: break
                            #
                            # While we *COULD* technically leverage that
                            # approach here, doing so would also mandate adding
                            # a number of intermediate tests, which would
                            # certainly reduce any performance gains.
                            # Ultimately, we avoid doing so by falling back to
                            # the standard approach. See also this relevant
                            # self-StackOverflow post:
                            #     https://stackoverflow.com/a/40054478/2809027
                            hint_curr_expr=register_typistry_tuple(
                                hint=tuple(hint_childs_nonpep),
                                # Inform this function it needn't attempt to
                                # uselessly omit duplicates, since the "typing"
                                # module already does so for all "Union"
                                # arguments. Well, that's nice.
                                is_types_unique=True,
                            )
                        ))

                # If this union is also subscripted by one or more
                # PEP-compliant arguments, generate less efficient code
                # type-checking these arguments.
                if hint_childs_pep:
                    #FIXME: Actually, it might be possible to precompute
                    #this validation at a much earlier time: namely, within
                    #the "beartype._decor._pep563" submodule. How? By
                    #totalizing the number of "[" and "," characters via
                    #the str.count() method, we should be able to obtain an
                    #efficient one-to-one relation between that number and
                    #the total number of child hints in a PEP-compliant
                    #type hint, which would then allow us to raise
                    #exceptions from that early-time submodule before this
                    #function is ever even called.
                    #
                    #This isn't terribly critical at the moment, but could
                    #become useful down the road. *shrug*
                    #FIXME: Inspection suggests the following trivial
                    #one-liner should suffice to compute the number of
                    #hints nested in any given hint (including that hint
                    #itself as well):
                    #    hint_repr = repr(hint)
                    #    hints_num = (
                    #        # Number of parent "typing" attributes nested
                    #        # in this hint, including this hint itself.
                    #        hint_repr.count('[') +
                    #        # Number of child "typing" attributes and
                    #        # non-"typing" types nested in this hint,
                    #        # excluding the last child arguments of all
                    #        # subscripted parent "typing" attributes.
                    #        hint_repr.count(',') +
                    #        # Number of child last arguments of all
                    #        #  subscripted parent "typing" attributes.
                    #        hint_repr.count(']')
                    #    )
                    #Sweet, eh?

                    # If adding fixed lists of metadata describing these
                    # arguments to the fixed list of such metadata would exceed
                    # the length of the latter, raise an exception.
                    if (
                        hints_meta_index_last + len(hint_childs_pep) >=
                        SIZE_BIG
                    ):
                        raise BeartypeDecorHintPepException(
                            '{} contains more than '
                            '{} "typing" types.'.format(
                                hint_root_label, SIZE_BIG))

                    # For each PEP-compliant child hint listed as a subscripted
                    # argument of this union...
                    for hint_child in hint_childs_pep:
                        # Placeholder string to be globally replaced by code
                        # type-checking the child pith against this child hint.
                        hint_child_placeholder = (
                            get_next_pep_hint_placeholder())

                        #FIXME: *WOOPS!* Premature optimization alert. Given
                        #that the fastest way to initialize a small fixed list
                        #is by slice-assigning from the equivalent tuple, we'd
                        #might as well dispense entirely with this fixed list
                        #and just use the tuple as is. Maybe? Let's profile.
                        #
                        #If faster, we can probably at least dispense with
                        #"_HINT_META_SIZE" above.

                        # List of metadata describing this child hint.
                        #
                        # Note that exhaustive profiling has demonstrated
                        # slice-assigning this list's items to be mildly
                        # faster than individually assigning these items:
                        #      $ command python3 -m timeit -s \
                        #      .     'muh_list = ["a", "b", "c", "d",]' \
                        #      .     'muh_list[:] = "e", "f", "g", "h"'
                        #      2000000 loops, best of 5: 131 nsec per loop
                        #      $ command python3 -m timeit -s \
                        #      .     'muh_list = ["a", "b", "c", "d",]' \
                        #      .     'muh_list[0] = "e"
                        #      . muh_list[1] = "f"
                        #      . muh_list[2] = "g"
                        #      . muh_list[3] = "h"'
                        #      2000000 loops, best of 5: 199 nsec per loop
                        hint_child_meta = acquire_fixed_list(_HINT_META_SIZE)
                        hint_child_meta[:] = (
                            hint_child,
                            hint_child_placeholder,
                            pith_curr_expr,
                            indent_child,
                        )

                        # Increment the 0-based index of metadata describing
                        # the last visitable hint in the "hints_meta" list
                        # *BEFORE* overwriting the existing metadata at this
                        # index.
                        #
                        # Note that this index is guaranteed to *NOT* exceed
                        # the fixed length of this list, by prior validation.
                        hints_meta_index_last += 1

                        # Inject this metadata at this index of this list.
                        hints_meta[hints_meta_index_last] = hint_child_meta

                        # Append code type-checking this argument.
                        #
                        # Defer formatting the "indent_curr" prefix into this
                        # code until below for efficiency.
                        func_curr_code += (
                            PEP_CODE_CHECK_HINT_UNION_ARG_PEP_format(
                                hint_child_placeholder=hint_child_placeholder))

                # If this code is *NOT* its initial value, this union is
                # subscripted by one or more unignorable arguments and the
                # above logic generated code type-checking these arguments. In
                # this case...
                if func_curr_code is not PEP_CODE_CHECK_HINT_UNION_PREFIX:
                    # Munge this code to...
                    func_curr_code = (
                        # Strip the erroneous suffix " or" appended by the last
                        # child hint from this code.
                        func_curr_code[:-3] +
                        # Suffix this code by the substring suffixing all such
                        # code.
                        PEP_CODE_CHECK_HINT_UNION_SUFFIX
                    # Format the "indent_curr" prefix into this code deferred
                    # above for efficiency.
                    ).format(indent_curr=indent_curr)
                # Else, this snippet is its initial value and thus ignorable.

            # ..............{ SEQUENCES                         }..............
            # If this hint is a standard sequence (e.g., "typing.List",
            # "typing.Sequence")...
            elif hint_curr_attr in TYPING_ATTRS_SEQUENCE_STANDARD:
                # Assert this attribute is isinstance()-able.
                assert hint_curr_attr in TYPING_ATTR_TO_TYPE_ORIGIN, (
                    '{} argumentless "typing" attribute{!r} '
                    'not isinstance()-able .'.format(
                        hint_child_label, hint_curr_attr))

                # Tuple of all subscripted arguments defining this sequence,
                # localized for both minor efficiency and major readability.
                #
                # Note that the "__args__" dunder attribute is *NOT* generally
                # guaranteed to exist for arbitrary PEP-compliant type hints
                # but is specifically guaranteed to exist for all standard
                # sequences including the argumentless "typing.List",
                # "typing.MutableSequence", and "typing.Sequence" attributes.
                # Ergo, this attribute is guaranteed to exist here.
                hint_childs = hint_curr.__args__

                # Assert this sequence was subscripted by exactly one argument.
                # Note that the "typing" module should have already guaranteed
                # this on our behalf. Still, we trust nothing and no one:
                #     >>> import typing as t
                #     >>> t.List[int, str]
                #     TypeError: Too many parameters for typing.List; actual 2, expected 1
                assert len(hint_childs) == 1, (
                    '{} sequence {!r} subscripted by '
                    'multiple arguments.'.format(hint_child_label, hint_curr))

                # Lone child hint of this parent hint.
                hint_child = hint_childs[0]

                # Python expression evaluating to this origin type when
                # accessed via the private "__beartypistry" parameter.
                hint_curr_expr = register_typistry_type(
                    # Origin type of this attribute if any *OR* raise an
                    # exception -- which should *NEVER* happen, as all standard
                    # sequences originate from an origin type.
                    get_hint_type_origin(hint_curr_attr))

                #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # CAVEATS: Synchronize changes here with logic below.
                #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                # If this child hint is *NOT* ignorable, deeply type-check both
                # the type of the current pith *AND* a randomly indexed item of
                # this pith. Specifically...
                if hint_child not in HINTS_IGNORABLE:
                    # Record that a pseudo-random integer is now required.
                    data.is_func_wrapper_needs_random_int = True

                    #FIXME: Optimize away. See above.

                    # If adding fixed lists of metadata describing this
                    # argument to the fixed list of such metadata would exceed
                    # the length of the latter, raise an exception.
                    if hints_meta_index_last + 1 >= SIZE_BIG:
                        raise BeartypeDecorHintPepException(
                            '{} contains more than '
                            '{} "typing" types.'.format(
                                hint_root_label, SIZE_BIG))

                    # Placeholder string to be globally replaced by code
                    # type-checking the child pith against this child hint.
                    hint_child_placeholder = get_next_pep_hint_placeholder()

                    # List of metadata describing this child hint. (See above.)
                    hint_child_meta = acquire_fixed_list(_HINT_META_SIZE)
                    hint_child_meta[:] = (
                        hint_child,
                        hint_child_placeholder,
                        # Python code snippet evaluating to a randomly indexed
                        # item of the current pith (i.e., standard sequence) to
                        # be type-checked against this child hint.
                        PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_PITH_CHILD_EXPR_format(
                            pith_curr_expr=pith_curr_expr),
                        indent_child,
                    )

                    # Increment the 0-based index of metadata describing the
                    # last visitable hint in the "hints_meta" list *BEFORE*
                    # overwriting the existing metadata at this index.
                    #
                    # Note that this index is guaranteed to *NOT* exceed the
                    # fixed length of this list, by prior validation.
                    hints_meta_index_last += 1

                    # Inject this metadata at this index of this list.
                    hints_meta[hints_meta_index_last] = hint_child_meta

                    #FIXME: Refactor to leverage f-strings after dropping
                    #Python 3.5 support, which are the optimal means of
                    #performing string formatting.

                    # Code type-checking the current pith against this type.
                    func_curr_code = (
                        PEP_CODE_CHECK_HINT_SEQUENCE_STANDARD_format(
                            indent_curr=indent_curr,
                            pith_curr_expr=pith_curr_expr,
                            hint_curr_expr=hint_curr_expr,
                            hint_child_placeholder=hint_child_placeholder,
                        ))
                # Else, this child hint is ignorable. In this case, fallback to
                # generating trivial code shallowly type-checking the current
                # pith as an instance of this origin type.
                else:
                    #FIXME: Refactor to leverage f-strings after dropping
                    #Python 3.5 support, which are the optimal means of
                    #performing string formatting.

                    # Code type-checking the current pith against this type.
                    func_curr_code = PEP_CODE_CHECK_HINT_NONPEP_TYPE_format(
                        pith_curr_expr=pith_curr_expr,
                        hint_curr_expr=hint_curr_expr,
                    )

            # ..............{ GENERICS                          }..............
            #FIXME: Implement support for generics (i.e., user-defined
            #subclasses) here similarly to how we currently handle "Union".
            #To do so, we'll want to call:
            #* The newly defined get_hint_pep_generic_bases() getter to form
            #  the set of all base classes to generate code intersected
            #  with " and ", much like "Union" hints united with " or ".
            #  When doing so, we'll want to assert that the returned tuple
            #  is non-empty. This doesn't warrant an exception, as the
            #  is_hint_pep_custom() tester will have already ensured this
            #  tuple to be non-empty.
            #* The existing get_hint_pep_args() getter to iterate the set
            #  of all concrete arguments parametrizing superclass type
            #  variables. This doesn't apply to us at the moment, of
            #  course, but we'll still want to note this somewhere.
            #* To treat the multiple inheritance case as analogous to the
            #  "Union" case. If one considers it, their structure should be
            #  nearly identical -- the sole difference being the usage of
            #  " and " rather than " or " as the boolean operator connecting
            #  the code generated for each child. In this respect, we could
            #  then consider each superclass of a user-defined subclass to be a
            #  "child hint" of that subclass.
            #* Add a new "elif hint_curr_attr is Generic:" test below, whose
            #  code would basically be identical to the existing "if
            #  hint_curr_attr is Union:" test above. Indeed, we should inspect
            #  that existing test and if, by inspection, we believe the two can
            #  indeed be fully unified, we should do so as follows:
            #  * Define above:
            #      HINT_ATTR_BOOL_TO_OPERATOR = {
            #          Generic: 'and',
            #          Union:   'or',
            #      )
            #  * Replace the hardcoded 'or' in both
            #    "PEP_CODE_CHECK_HINT_UNION_ARG_PEP" and
            #    "PEP_CODE_CHECK_HINT_UNION_ARG_NONPEP" with a
            #    "{hint_curr_attr_bool_operator}" format variable.
            #  * Rename the "PEP_CODE_CHECK_HINT_UNION_*" suite of globals to
            #    "PEP_CODE_CHECK_HINT_BOOL_*" instead.
            #  * Refactor above:
            #      # Refactor this...
            #      if hint_curr_attr is Union:
            #
            #      # ...into this:
            #      hint_curr_attr_bool_operator = HINT_ATTR_BOOL_TO_OPERATOR.get(
            #          hint_curr_attr, None)
            #      if hint_curr_attr_bool_operator is not None:
            #
            #Welp, that's pretty brilliant. Nearly instantaneous support for
            #multiple inheritance in a generically orthogonal manner.

            # If this is a generic (i.e., user-defined class subclassing one or
            # more "typing" pseudo-superclasses)...
            # # elif hint_curr_attr is Generic:
            # #     pass

            # ..............{ FALLBACK                          }..............
            # Else, fallback to generating trivial code shallowly type-checking
            # the current pith as an instance of the PEP-noncompliant
            # non-"typing" origin class originating this argumentless "typing"
            # attribute (e.g., "list" for the attribute "List" associated with
            # the hint "List[int]").
            #
            # This fallback implements nominal implicit support for
            # argumentless "typing" attributes currently *NOT* explicitly
            # supported above.
            #
            # Note that this fallback already perfectly type-checks the proper
            # subset of argumentless typing attributes originating from origin
            # types that accept *NO* subscripted arguments, including:
            # * "typing.ByteString", which accepts *NO* subscripted arguments.
            #   "typing.ByteString" is simply an alias for the
            #   "collections.abc.ByteString" abstract base class (ABC) and thus
            #   already perfectly handled by this fallback logic.
            #
            # Ergo, this fallback *MUST* thus be preserved in perpetuity --
            # even after we explicitly deeply type-check all other argumentless
            # typing attributes originating from origin types above.
            else:
                # Assert this attribute is isinstance()-able.
                assert hint_curr_attr in TYPING_ATTR_TO_TYPE_ORIGIN, (
                    '{} argumentless "typing" attribute{!r} '
                    'not isinstance()-able .'.format(
                        hint_child_label, hint_curr_attr))

                #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # CAVEATS: Synchronize changes here with logic below.
                #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                #FIXME: Refactor to leverage f-strings after dropping
                #Python 3.5 support, which are the optimal means of
                #performing string formatting.

                # Code type-checking the current pith against this class.
                func_curr_code = PEP_CODE_CHECK_HINT_NONPEP_TYPE_format(
                    pith_curr_expr=pith_curr_expr,
                    # Python expression evaluating to this class when accessed
                    # via the private "__beartypistry" parameter.
                    hint_curr_expr=register_typistry_type(
                        # Origin type of this attribute if any *OR* raise an
                        # exception -- which should *NEVER* happen, as this
                        # attribute was validated above to be supported.
                        get_hint_type_origin(hint_curr_attr)
                    ),
                )
        # Else, this hint is *NOT* PEP-compliant.

        # ................{ CLASSES                           }................
        # If this hint is a non-"typing" class...
        #
        # Note that:
        #
        # * This test is intentionally performed *AFTER* that testing whether
        #   this hint is PEP-compliant, thus guaranteeing this hint to be a
        #   PEP-noncompliant non-"typing" class rather than a PEP-compliant
        #   type hint originating from such a class. Since many hints are both
        #   PEP-compliant *AND* originate from such a class (e.g., the "List"
        #   in "List[int]", PEP-compliant but originating from the
        #   PEP-noncompliant builtin class "list"), testing these hints first
        #   for PEP-compliance ensures we generate non-trivial code deeply
        #   type-checking these hints instead of trivial code only shallowly
        #   type-checking the non-"typing" classes from which they originate.
        # * This class is guaranteed to be a subscripted argument of a
        #   PEP-compliant type hint (e.g., the "int" in "Union[Dict[str, str],
        #   int]") rather than the root type hint. Why? Because if this class
        #   were the root type hint, it would have already been passed into a
        #   faster submodule generating PEP-noncompliant code instead.
        elif isinstance(hint_curr, type):
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # CAVEATS: Synchronize changes here with similar logic above.
            #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            #FIXME: Refactor to leverage f-strings after dropping Python 3.5
            #support, which are the optimal means of performing string
            #formatting.

            # Code type-checking the current pith against this class.
            func_curr_code = PEP_CODE_CHECK_HINT_NONPEP_TYPE_format(
                pith_curr_expr=pith_curr_expr,
                # Python expression evaluating to this class when accessed via
                # the private "__beartypistry" parameter.
                hint_curr_expr=register_typistry_type(hint_curr),
            )

        # Else, this hint is neither PEP-compliant *NOR* a class. In this
        # case, raise an exception. Note that:
        #
        # * This should *NEVER* happen, as the "typing" module goes to great
        #   lengths to validate the integrity of PEP-compliant types at
        #   declaration time.
        # * The higher-level die_unless_hint_nonpep() validator is
        #   intentionally *NOT* called here, as doing so would permit both:
        #   * PEP-noncompliant forward references, which could admittedly be
        #     disabled by passing "is_str_valid=False" to that call.
        #   * PEP-noncompliant tuple unions, which currently *CANNOT* be
        #     disabled by passing such an option to that call.
        else:
            raise BeartypeDecorHintPepException(
                '{} {!r} not PEP-compliant (i.e., '
                'neither "typing" object nor non-"typing" class).'.format(
                    hint_child_label, hint_curr))

        # ................{ CLEANUP                           }................
        # Inject this code into the body of this wrapper.
        func_code = func_code.replace(
            hint_curr_placeholder, func_curr_code)

        # Release the metadata describing the previously visited hint and
        # nullify this metadata in its list for safety.
        release_fixed_list(hint_curr_meta)
        hints_meta[hints_meta_index_curr] = None

        # Increment the 0-based index of metadata describing the next visited
        # hint in the "hints_meta" list *BEFORE* visiting this hint but *AFTER*
        # performing all other logic for the currently visited hint, implying
        # this should be the last statement of this iteration.
        hints_meta_index_curr += 1

    # ..................{ CLEANUP                           }..................
    # Release the fixed list of all such metadata.
    release_fixed_list(hints_meta)

    # If the Python code snippet to be returned remains unchanged from its
    # initial value, the breadth-first search above failed to generate code. In
    # this case, raise an exception.
    #
    # Note that this test is inexpensive, as the third character of the
    # "func_root_code" code snippet is guaranteed to differ from that of
    # "func_code" code snippet if this function behaved as expected, which it
    # absolutely should have... but may not have, which is why we're testing.
    if func_code == func_root_code:
        raise BeartypeDecorHintPepException(
            '{} not type-checked.'.format(hint_root_label))
    # Else, the breadth-first search above successfully generated code.

    # Return this snippet.
    return func_code