#!/usr/bin/env python3
# --------------------( LICENSE                           )--------------------
# Copyright (c) 2014-2021 Beartype authors.
# See "LICENSE" for further details.

'''
**NumPy-specific PEP-noncompliant type hints** (i.e., unofficial type hints
declared by the third-party :mod:`numpy` package) test data.

These hints include:

* **Typed NumPy arrays** (i.e., subscriptions of the
  :attr:`numpy.typing.NDArray` type hint factory).

Caveats
----------
Although NumPy-specific type hints are technically PEP-noncompliant, the
:mod:`beartype` codebase currently treats these hints as PEP-compliant to
dramatically simplify code generation for these hints. Ergo, so we do.
'''

# ....................{ IMPORTS                           }....................
from beartype._util.py.utilpyversion import IS_PYTHON_AT_LEAST_3_9
from beartype._util.data.hint.pep.sign.datapepsigns import (
    HintSignNumpyArray,
)
from beartype_test.a00_unit.data.hint.util.data_hintmetacls import (
    PepHintMetadata,
    HintPithSatisfiedMetadata,
    HintPithUnsatisfiedMetadata,
)
from beartype_test.util.mod.pytmodoptional import (
    is_package_numpy_typing_ndarray_supported)

# ....................{ ADDERS                            }....................
def add_data(data_module: 'ModuleType') -> None:
    '''
    Add :mod:`numpy`-specific type hint test data to various global containers
    declared by the passed module.

    Parameters
    ----------
    data_module : ModuleType
        Module to be added to.
    '''

    # If @beartype does *NOT* support the "numpy.typing.NDArray" type hint
    # under the active Python, reduce to a noop.
    if not is_package_numpy_typing_ndarray_supported():
        return
    # If @beartype supports the "numpy.typing.NDArray" type hint under the
    # active Python.

    # ..................{ IMPORTS                           }..................
    # Defer NumPy-specific imports.
    from numpy import asarray, dtype, float64
    from numpy.typing import NDArray

    # ..................{ TUPLES                            }..................
    # Add NumPy-specific test type hints to this tuple global.
    data_module.HINTS_PEP_META.extend((
        # ................{ NUMPY ~ array                     }................
        # NumPy array subscripted by a true data type.
        PepHintMetadata(
            hint=NDArray[dtype(float64)],
            pep_sign=HintSignNumpyArray,
            # "NDArray" is implemented as:
            # * Under Python >= 3.9, a PEP 585-compliant generic.
            # * Under Python < 3.9, a pure-Python generic backport.
            is_pep585_builtin=IS_PYTHON_AT_LEAST_3_9,
            is_type_typing=False,
            is_typing=False,
            piths_satisfied_meta=(
                # NumPy array containing only 64-bit floats.
                HintPithSatisfiedMetadata(
                    asarray((1.0, 1.5, 1.8333, 2.08333, 2.28333, 2.45,)),
                ),
            ),
            piths_unsatisfied_meta=(
                # String constant.
                HintPithUnsatisfiedMetadata(
                    pith='Aggrandizing strifes with‐in',
                    # Match that the exception message raised for this object
                    # embeds the representation of the expected class.
                    exception_str_match_regexes=(r'\bnumpy\.ndarray\b',),
                ),
                # NumPy array containing only 64-bit integers.
                HintPithUnsatisfiedMetadata(
                    pith=((4, 36, 624, 3744, 5108, 10200, 54912, 123552,)),
                    # Match that the exception message raised for this object
                    # embeds the representation of the expected data type.
                    exception_str_match_regexes=(r'\bfloat64\b',),
                ),
            ),
        ),

        # NumPy array subscripted by a scalar data type. Since scalar data
        # types are *NOT* true data types, this constitutes an edge case.
        PepHintMetadata(
            hint=NDArray[float64],
            pep_sign=HintSignNumpyArray,
            is_pep585_builtin=IS_PYTHON_AT_LEAST_3_9,
            is_type_typing=False,
            is_typing=False,
            piths_satisfied_meta=(
                # NumPy array containing only 64-bit floats.
                HintPithSatisfiedMetadata(
                    asarray((2.0, 2.5, 2.6, 2.7083, 2.716, 2.71805,)),
                ),
            ),
            piths_unsatisfied_meta=(
                # String constant.
                HintPithUnsatisfiedMetadata(
                    pith='Silver, ore, and almost dazedly aggro‐',
                    # Match that the exception message raised for this object
                    # embeds the representation of the expected class.
                    exception_str_match_regexes=(r'\bnumpy\.ndarray\b',),
                ),
                # NumPy array containing only 64-bit integers.
                HintPithUnsatisfiedMetadata(
                    pith=((1, 1, 1, 1, 2, 3, 6, 11, 23, 47, 106, 235, 551,)),
                    # Match that the exception message raised for this object
                    # embeds the representation of the expected data type.
                    exception_str_match_regexes=(r'\bfloat64\b',),
                ),
            ),
        ),
    ))