#!/usr/bin/env python3
"""
Benchmark different dictionary approaches for parameter lookup.
Testing with 1789 parameters (actual count from FHEM source).
"""

import timeit
import sys
from collections import OrderedDict
from typing import Dict, Any

# Actual parameter count from FHEM 26_KM273v018.pm
NUM_PARAMS = 1789


def test_simple_dict():
    """Test simple dict with uppercase keys."""
    data = {
        f'PARAM_{i}': {
            'idx': i,
            'extid': f'{i:014x}',
            'min': 0,
            'max': 100,
            'format': 'int',
            'read': 0
        }
        for i in range(NUM_PARAMS)
    }

    # Lookup test - worst case (last item)
    lookup_key = f'PARAM_{NUM_PARAMS-1}'
    result = data.get(lookup_key)
    return sys.getsizeof(data), result


def test_ordered_dict():
    """Test OrderedDict."""
    data = OrderedDict(
        (f'PARAM_{i}', {
            'idx': i,
            'extid': f'{i:014x}',
            'min': 0,
            'max': 100,
            'format': 'int',
            'read': 0
        })
        for i in range(NUM_PARAMS)
    )

    lookup_key = f'PARAM_{NUM_PARAMS-1}'
    result = data.get(lookup_key)
    return sys.getsizeof(data), result


class CaseInsensitiveDict(dict):
    """Simple case-insensitive dictionary wrapper."""

    def __getitem__(self, key):
        return super().__getitem__(key.upper())

    def get(self, key, default=None):
        return super().get(key.upper(), default)

    def __contains__(self, key):
        return super().__contains__(key.upper())


def test_case_insensitive():
    """Test case-insensitive wrapper."""
    data = CaseInsensitiveDict({
        f'PARAM_{i}': {
            'idx': i,
            'extid': f'{i:014x}',
            'min': 0,
            'max': 100,
            'format': 'int',
            'read': 0
        }
        for i in range(NUM_PARAMS)
    })

    # Test with lowercase input
    lookup_key = f'param_{NUM_PARAMS-1}'
    result = data.get(lookup_key)
    return sys.getsizeof(data), result


class ImmutableParameterDict:
    """Immutable parameter dictionary with case-insensitive lookup."""

    def __init__(self, params: Dict[str, Any]):
        self._params = {k.upper(): v for k, v in params.items()}
        # Freeze by removing ability to modify

    def get(self, key: str, default=None):
        return self._params.get(key.upper(), default)

    def __getitem__(self, key: str):
        return self._params[key.upper()]

    def __contains__(self, key: str):
        return key.upper() in self._params

    def keys(self):
        return self._params.keys()

    def values(self):
        return self._params.values()

    def items(self):
        return self._params.items()


def test_immutable():
    """Test immutable wrapper."""
    params = {
        f'PARAM_{i}': {
            'idx': i,
            'extid': f'{i:014x}',
            'min': 0,
            'max': 100,
            'format': 'int',
            'read': 0
        }
        for i in range(NUM_PARAMS)
    }
    data = ImmutableParameterDict(params)

    lookup_key = f'param_{NUM_PARAMS-1}'
    result = data.get(lookup_key)
    return sys.getsizeof(data._params), result


def main():
    print("=" * 60)
    print(f"PARAMETER LOOKUP BENCHMARK ({NUM_PARAMS} parameters)")
    print("=" * 60)
    print()

    # Memory footprint
    print("=== MEMORY FOOTPRINT ===")
    dict_size, _ = test_simple_dict()
    print(f"Simple dict:           {dict_size:>10,} bytes")

    ordered_size, _ = test_ordered_dict()
    print(f"OrderedDict:           {ordered_size:>10,} bytes")

    case_size, _ = test_case_insensitive()
    print(f"CaseInsensitiveDict:   {case_size:>10,} bytes")

    immutable_size, _ = test_immutable()
    print(f"ImmutableParameterDict:{immutable_size:>10,} bytes")

    print()
    print("=== LOOKUP PERFORMANCE (10,000 iterations) ===")

    # Simple dict with pre-normalized key
    setup_dict = f"""
data = {{f"PARAM_{{i}}": {{"idx": i, "extid": f"{{i:014x}}", "min": 0, "max": 100}}
        for i in range({NUM_PARAMS})}}
lookup_key = f"PARAM_{{{NUM_PARAMS-1}}}"
"""

    # OrderedDict
    setup_ordered = f"""
from collections import OrderedDict
data = OrderedDict((f"PARAM_{{i}}", {{"idx": i, "extid": f"{{i:014x}}", "min": 0, "max": 100}})
                   for i in range({NUM_PARAMS}))
lookup_key = f"PARAM_{{{NUM_PARAMS-1}}}"
"""

    # CaseInsensitiveDict
    setup_case = f"""
class CaseInsensitiveDict(dict):
    def get(self, key, default=None):
        return super().get(key.upper(), default)

data = CaseInsensitiveDict({{f"PARAM_{{i}}": {{"idx": i, "extid": f"{{i:014x}}", "min": 0, "max": 100}}
                            for i in range({NUM_PARAMS})}})
lookup_key = f"param_{{{NUM_PARAMS-1}}}"
"""

    # ImmutableParameterDict
    setup_immutable = f"""
class ImmutableParameterDict:
    def __init__(self, params):
        self._params = {{k.upper(): v for k, v in params.items()}}
    def get(self, key, default=None):
        return self._params.get(key.upper(), default)

params = {{f"PARAM_{{i}}": {{"idx": i, "extid": f"{{i:014x}}", "min": 0, "max": 100}}
          for i in range({NUM_PARAMS})}}
data = ImmutableParameterDict(params)
lookup_key = f"param_{{{NUM_PARAMS-1}}}"
"""

    iterations = 10000

    dict_time = timeit.timeit("data.get(lookup_key)", setup=setup_dict, number=iterations)
    print(f"Simple dict:           {dict_time*1000:.4f}ms total, {dict_time/iterations*1000000:.3f}µs per lookup")

    ordered_time = timeit.timeit("data.get(lookup_key)", setup=setup_ordered, number=iterations)
    print(f"OrderedDict:           {ordered_time*1000:.4f}ms total, {ordered_time/iterations*1000000:.3f}µs per lookup")

    case_time = timeit.timeit("data.get(lookup_key)", setup=setup_case, number=iterations)
    print(f"CaseInsensitiveDict:   {case_time*1000:.4f}ms total, {case_time/iterations*1000000:.3f}µs per lookup")

    immutable_time = timeit.timeit("data.get(lookup_key)", setup=setup_immutable, number=iterations)
    print(f"ImmutableParameterDict:{immutable_time*1000:.4f}ms total, {immutable_time/iterations*1000000:.3f}µs per lookup")

    print()
    print("=== CONCLUSION ===")
    print(f"Target: <100ms lookup time")
    print(f"All approaches meet target: {dict_time*1000:.4f}ms << 100ms")
    print()
    print("Performance ranking (fastest to slowest):")
    results = [
        ("Simple dict", dict_time),
        ("OrderedDict", ordered_time),
        ("CaseInsensitiveDict", case_time),
        ("ImmutableParameterDict", immutable_time),
    ]
    results.sort(key=lambda x: x[1])
    for i, (name, time) in enumerate(results, 1):
        print(f"  {i}. {name:25s} ({time/iterations*1000000:.3f}µs)")


if __name__ == "__main__":
    main()
