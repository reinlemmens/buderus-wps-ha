# Parameter Lookup: Decision Summary

**Feature**: 005-can-parameter-access
**Date**: 2025-10-24
**Parameters**: 1,789 (actual count from FHEM source)
**Requirement**: <100ms lookup time (NFR-005)

---

## Decision

### ✅ Use Simple Dict with Case-Insensitive Wrapper

```python
from types import MappingProxyType

class ParameterRegistry:
    def __init__(self, parameters):
        self._params = {param['text'].upper(): param for param in parameters}
        self.params = MappingProxyType(self._params)  # Immutable view

    def get(self, name, default=None):
        return self.params.get(name.upper(), default)
```

---

## Quick Comparison

| Approach | Speed | Memory | Complexity | Verdict |
|----------|-------|--------|------------|---------|
| **Simple dict** ⭐ | **0.5-1µs** | **73KB** | **Low** | **RECOMMENDED** |
| OrderedDict | 1-1.5µs | 85KB | Low | No benefit |
| Cached lookup | 0.5µs | 146KB | Medium | Overkill |
| SQLite | 100-500µs | 300KB | High | Massive overkill |

**Target**: <100,000µs (100ms)
**Result**: All approaches are 100,000x+ faster than needed

---

## Rationale

### 1. Performance is Not a Concern

- **Requirement**: <100 milliseconds
- **Simple dict**: ~0.001 milliseconds (1 microsecond)
- **Margin**: 100,000x faster than required

Even the worst approach (SQLite) is still 200x faster than needed.

### 2. Memory is Not a Concern

- **Total memory**: ~600KB for 1,789 parameters
- **Context**: Modern Python baseline is 10-100MB
- **Percentage**: 0.6% of 100MB

### 3. Simplicity Wins

Python dict is:
- Built-in, well-tested, O(1) lookup
- Understood by every Python developer
- Minimal code (~20 lines with wrapper)
- Easy to test and maintain

### 4. Immutability for Safety

- `MappingProxyType` prevents accidental modification
- No performance penalty for reads
- Clear intent in code

---

## Why Not the Alternatives?

### OrderedDict
- ❌ No benefit in Python 3.7+ (regular dict preserves order)
- ❌ Slightly slower and uses more memory
- ❌ No functional advantage

### Custom Caching
- ❌ Doubles memory usage
- ❌ Adds complexity for <0.0001ms improvement
- ❌ `.upper()` is already extremely fast (~50ns)
- ❌ Textbook premature optimization

### SQLite In-Memory
- ❌ 100-1000x slower than dict (still meets requirement, but why?)
- ❌ Complex setup and maintenance
- ❌ Requires SQL knowledge
- ❌ Harder to test
- ❌ Database is for persistent storage, not in-memory lookup

---

## Implementation Details

### Case Normalization Strategy

**Decision**: Normalize keys at load time, normalize input at access time

```python
# At load time (once)
self._params = {param['text'].upper(): param for param in parameters}

# At access time (per request)
def get(self, name, default=None):
    return self.params.get(name.upper(), default)  # ← 50ns overhead
```

**Why**:
- Keys normalized once at startup (one-time cost)
- Input normalized per-lookup (50 nanosecond cost = negligible)
- Allows case-insensitive input: `get("access_level")` or `get("ACCESS_LEVEL")`

### Error Handling

```python
def get(self, name, default=None):
    """Soft lookup - returns default if not found"""
    return self.params.get(name.upper(), default)

def __getitem__(self, name):
    """Strict lookup - raises KeyError if not found"""
    key = name.upper()
    if key not in self.params:
        raise KeyError(f"Parameter '{name}' not found")
    return self.params[key]
```

### Thread Safety

- ✅ **Safe for concurrent reads** (dict is immutable after init)
- ❌ **NOT safe for concurrent writes** (not supported per spec)
- 📝 **Documented assumption**: Single-threaded sequential usage

---

## Performance Estimates

### Lookup Time (1,789 parameters)

```
Simple dict:        0.5-1.0 microseconds
String .upper():    0.05-0.1 microseconds
Total:              0.55-1.1 microseconds

Target:             100,000 microseconds (100ms)
Margin:             ~100,000x faster
```

### Memory Footprint

```
Dict structure:     ~73 KB
Parameter data:     ~350 KB (200 bytes × 1,789 params)
Total:              ~423 KB

Context:            <0.5% of typical Python app memory
```

### Startup Time

```
Load 1,789 params:  1-2 milliseconds
Create dict:        0.5-1 milliseconds
Total:              <3 milliseconds

Context:            Negligible compared to CAN bus init
```

---

## Validation Strategy

While theoretical analysis proves dict is sufficient, validate with:

```python
import timeit

# Test lookup performance
def benchmark():
    params = load_fhem_parameters()  # 1,789 params
    registry = ParameterRegistry(params)

    # Test various cases
    tests = [
        "ACCESS_LEVEL",         # Uppercase
        "access_level",         # Lowercase
        "Access_Level",         # Mixed case
        "COMPRESSOR_ALARM",     # Different param
        "invalid_param",        # Not found
    ]

    times = []
    for name in tests:
        t = timeit.timeit(lambda: registry.get(name), number=10000)
        avg_us = (t / 10000) * 1000000
        times.append((name, avg_us))
        print(f"{name:30s} {avg_us:6.2f}µs")

    return times
```

**Expected results**:
- All lookups: <2 microseconds
- Target requirement: <100,000 microseconds
- Conclusion: Passes with 50,000x+ margin

---

## Questions Answered

### Q: Do we need to optimize for 1,789 parameters?
**A**: No. Python dict handles millions of keys efficiently.

### Q: Should we cache the `.upper()` operation?
**A**: No. It takes 50 nanoseconds - optimization would cost more than it saves.

### Q: What about thread safety?
**A**: Use `MappingProxyType` for immutability. Spec says single-threaded anyway.

### Q: Should we use a database?
**A**: No. Dict is 1000x faster and simpler for this use case.

### Q: What about fuzzy matching or autocomplete?
**A**: Out of scope per spec. Can add later if needed.

---

## References

- **Spec**: `/Users/rein/Documents/buderus-wps-ha/specs/005-can-parameter-access/spec.md`
  - NFR-005: <100ms lookup time
  - FR-005: Case-insensitive input, uppercase storage
- **Source data**: `/Users/rein/Documents/buderus-wps-ha/fhem/26_KM273v018.pm`
  - 1,789 parameters in `@KM273_elements_default`
- **Related feature**: 002-buderus-wps-python-class (parameter definitions)

---

## Next Steps

1. ✅ Decision documented
2. ⏭️ Implement `ParameterRegistry` class
3. ⏭️ Add unit tests (test case-insensitivity, error handling)
4. ⏭️ Integrate with Feature 002 parameter loading
5. ⏭️ Add to CLI for parameter access commands

---

**Status**: Research complete, ready for implementation
**Confidence**: Very high - dict is the obvious and correct choice
