#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**Beartype-specific PEP-noncompliant type hints** (i.e., unofficial type hints
supported *only* by the :mod:`beartype.beartype` decorator) test data.

These hints include:

* **Tuple unions** (i.e., tuples containing *only* standard classes and
  forward references to standard classes).
'''

# ....................{ IMPORTS                           }....................
from beartype_test.a00_unit.data.hint.util.data_hintmetacls import (
    NonPepHintMetadata,
    HintPithSatisfiedMetadata,
    HintPithUnsatisfiedMetadata,
)

# ....................{ ADDERS                            }....................
def add_data(data_module: 'ModuleType') -> None:
    '''
    Add :mod:`beartype`-specific PEP-noncompliant type hint test data to
    various global containers declared by the passed module.

    Parameters
    ----------
    data_module : ModuleType
        Module to be added to.
    '''

    # ..................{ TUPLES                            }..................
    # Add beartype-specific PEP-noncompliant test type hints to this dictionary
    # global.
    data_module.HINTS_NONPEP_META.extend((
        # ................{ TUPLE UNION                       }................
        # Tuple union of one standard class.
        NonPepHintMetadata(
            hint=(str,),
            piths_satisfied_meta=(
                # String constant.
                HintPithSatisfiedMetadata('Pinioned coin tokens'),
            ),
            piths_unsatisfied_meta=(
                # Byte-string constant.
                HintPithUnsatisfiedMetadata(
                    pith=b'Murkily',
                    # Match that the exception message raised for this pith
                    # declares the types *NOT* satisfied by this object.
                    exception_str_match_regexes=(
                        r'\bstr\b',
                    ),
                    # Match that the exception message raised for this pith
                    # does *NOT* contain a newline or bullet delimiter.
                    exception_str_not_match_regexes=(
                        r'\n',
                        r'\*',
                    ),
                ),
            ),
        ),

        # Tuple union of two or more standard classes.
        NonPepHintMetadata(
            hint=(int, str),
            piths_satisfied_meta=(
                # Integer constant.
                HintPithSatisfiedMetadata(12),
                # String constant.
                HintPithSatisfiedMetadata('Smirk‐opined — openly'),
            ),
            piths_unsatisfied_meta=(
                # Byte-string constant.
                HintPithUnsatisfiedMetadata(
                    pith=b'Betokening',
                    # Match that the exception message raised for this object
                    # declares the types *NOT* satisfied by this object.
                    exception_str_match_regexes=(
                        r'\bint\b',
                        r'\bstr\b',
                    ),
                    # Match that the exception message raised for this object
                    # does *NOT* contain a newline or bullet delimiter.
                    exception_str_not_match_regexes=(
                        r'\n',
                        r'\*',
                    ),
                ),
            ),
        ),

        # ................{ TYPE                              }................
        # Builtin type.
        NonPepHintMetadata(
            hint=str,
            piths_satisfied_meta=(
                # String constant.
                HintPithSatisfiedMetadata('Glassily lassitudinal bȴood-'),
            ),
            piths_unsatisfied_meta=(
                # Byte-string constant.
                HintPithUnsatisfiedMetadata(
                    pith=b'Stains, disdain-fully ("...up-stairs!"),',
                    # Match that the exception message raised for this pith
                    # declares the types *NOT* satisfied by this object.
                    exception_str_match_regexes=(
                        r'\bstr\b',
                    ),
                    # Match that the exception message raised for this pith
                    # does *NOT* contain...
                    exception_str_not_match_regexes=(
                        # A newline.
                        r'\n',
                        # A bullet delimiter.
                        r'\*',
                        # Descriptive terms applied only to non-builtin types.
                        r'\bprotocol\b',
                        # The double-quoted name of this builtin type.
                        r'"str"',
                    ),
                ),
            ),
        ),
    ))