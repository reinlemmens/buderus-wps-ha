# Python Data Structure Optimization Research
## Fast Parameter Lookup by Name (1789 Parameters)

**Context**: Buderus WPS Heat Pump Parameter Access (Feature 005)
**Target**: <100ms lookup time for 400+ parameters
**Actual Count**: 1,789 parameters from FHEM source

---

## Executive Summary

**Decision**: Use a simple `dict` with uppercase keys and normalize input at access time via a thin wrapper class.

**Rationale**:
- Python dictionaries have O(1) average-case lookup performance
- For 1,789 parameters, lookup time is typically <1 microsecond
- Simple dict uses ~73KB memory (well within reasonable limits)
- Case normalization overhead (`.upper()`) is negligible compared to 100ms target
- No optimization needed - vanilla dict is 100,000x faster than requirement

**Performance Estimate**:
- **Lookup time**: 0.001ms (1 microsecond) - 100,000x faster than 100ms target
- **Memory footprint**: ~73KB for dict structure + parameter data
- **Conclusion**: Even the simplest approach exceeds requirements by orders of magnitude

---

## 1. Data Structure Comparison

### Option A: Simple Dict with Uppercase Keys ⭐ RECOMMENDED

```python
class ParameterRegistry:
    """Simple parameter registry with case-insensitive lookup."""

    def __init__(self, parameters):
        # Store with uppercase keys at load time
        self._params = {
            param['text'].upper(): param
            for param in parameters
        }

    def get(self, name, default=None):
        """Get parameter by name (case-insensitive)."""
        return self._params.get(name.upper(), default)

    def __getitem__(self, name):
        """Dict-like access."""
        return self._params[name.upper()]
```

**Pros**:
- Simplest implementation (< 20 lines)
- O(1) average-case lookup
- Minimal memory overhead
- Pythonic and idiomatic
- Easy to test and debug

**Cons**:
- Requires `.upper()` call on every lookup (negligible cost)

**Performance**:
- Lookup time: ~0.5-1.0 microseconds
- Memory: ~73KB for 1,789 entries (dict overhead only)
- Thread-safe for reads (if dict is not modified after initialization)

---

### Option B: Collections.OrderedDict

```python
from collections import OrderedDict

class ParameterRegistry:
    def __init__(self, parameters):
        self._params = OrderedDict(
            (param['text'].upper(), param)
            for param in parameters
        )
```

**Pros**:
- Preserves insertion order (Python 3.7+ dicts do this anyway)
- Same O(1) lookup as regular dict

**Cons**:
- Slightly higher memory overhead (~15-20% more than dict)
- No significant benefit for this use case
- Marginally slower than plain dict

**Performance**:
- Lookup time: ~1.0-1.5 microseconds (slightly slower)
- Memory: ~85-90KB for 1,789 entries

**Verdict**: Not recommended - no benefit over plain dict in Python 3.7+

---

### Option C: Custom Class with Caching

```python
class CachedParameterRegistry:
    def __init__(self, parameters):
        self._params = {p['text'].upper(): p for p in parameters}
        self._lookup_cache = {}  # Cache normalized lookups

    def get(self, name, default=None):
        normalized = name.upper()
        if normalized not in self._lookup_cache:
            self._lookup_cache[normalized] = self._params.get(normalized, default)
        return self._lookup_cache[normalized]
```

**Pros**:
- Caches normalized key lookups (theoretical optimization)

**Cons**:
- Adds complexity for no measurable benefit
- Double memory usage (cache duplicates references)
- `.upper()` is already extremely fast (~50-100 nanoseconds)
- Over-engineering for this problem

**Performance**:
- First lookup: ~1.0 microsecond
- Cached lookup: ~0.5 microseconds (marginal improvement)
- Memory: ~146KB (doubles memory due to cache)

**Verdict**: Not recommended - premature optimization

---

### Option D: SQLite In-Memory Database

```python
import sqlite3

class SQLParameterRegistry:
    def __init__(self, parameters):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute('''
            CREATE TABLE parameters (
                name TEXT PRIMARY KEY COLLATE NOCASE,
                idx INTEGER,
                extid TEXT,
                min INTEGER,
                max INTEGER,
                format TEXT,
                read INTEGER
            )
        ''')
        # Insert all parameters...

    def get(self, name):
        cursor = self.conn.execute(
            'SELECT * FROM parameters WHERE name = ?', (name,)
        )
        return cursor.fetchone()
```

**Pros**:
- Built-in case-insensitive collation (COLLATE NOCASE)
- SQL query capabilities (filtering, sorting)
- Mature, well-tested technology

**Cons**:
- Significant setup complexity
- Much slower than dict (100-1000x slower)
- Overkill for simple key-value lookup
- Requires SQL knowledge for maintenance
- Harder to test and debug

**Performance**:
- Lookup time: ~100-500 microseconds (100x slower than dict)
- Memory: ~200-300KB (database overhead)

**Verdict**: Not recommended - massive overkill for this use case

---

## 2. Case Normalization Strategy

### Where to Normalize: **At Load Time for Keys, At Access Time for Input**

**Recommended approach**:

```python
class ParameterRegistry:
    def __init__(self, parameters):
        # Normalize ONCE at load time
        self._params = {
            param['text'].upper(): param
            for param in parameters
        }

    def get(self, name, default=None):
        # Normalize input at access time
        return self._params.get(name.upper(), default)
```

**Rationale**:
1. **Keys normalized at load time**: One-time cost, happens once at startup
2. **Input normalized at access time**: Allows case-insensitive input
3. **Cost of `.upper()`**: ~50-100 nanoseconds (completely negligible)

### Invalid Parameter Name Handling

```python
def get(self, name, default=None):
    """Get parameter by name, return None if not found."""
    if not isinstance(name, str):
        raise TypeError(f"Parameter name must be string, got {type(name)}")

    normalized = name.upper()
    param = self._params.get(normalized)

    if param is None and default is None:
        # Optionally provide helpful error message
        similar = self._find_similar_names(normalized)  # Optional
        if similar:
            raise KeyError(
                f"Parameter '{name}' not found. Did you mean: {', '.join(similar)}?"
            )
        raise KeyError(f"Parameter '{name}' not found")

    return param if param is not None else default
```

**Error handling strategy**:
- Fast path: Use `.get()` method with default=None for optional lookup
- Strict path: Use `[]` syntax or explicit error checking for required parameters
- User-friendly: Provide "did you mean?" suggestions for typos (optional feature)

---

## 3. Memory vs Speed Tradeoffs

### Memory Footprint Analysis (1,789 parameters)

```
Base dict structure:     ~73 KB
Parameter data:          ~350 KB (estimated: 200 bytes per param)
Total:                   ~423 KB
```

**Breakdown**:
- Dict overhead: ~40 bytes per entry = 72KB
- Each parameter contains:
  - `idx`: 28 bytes (int object)
  - `extid`: 63 bytes (14-char string)
  - `min`/`max`: 56 bytes (2 int objects)
  - `format`: ~55 bytes (string)
  - `read`: 28 bytes (int)
  - `text`: ~70 bytes (avg 25-char string)
  - Total per param: ~300 bytes

**Total memory**: ~500-600 KB for entire registry

**Context**: This is trivial memory usage
- Modern Python applications: 10-100+ MB baseline
- 600 KB is 0.06% of 1 GB
- Heat pump application: likely <10 MB total
- **Conclusion**: Memory is not a constraint

### Speed Analysis

**Python dict lookup performance**:
- Hash computation: ~50 nanoseconds
- Hash table lookup: ~50-100 nanoseconds
- String `.upper()`: ~50-100 nanoseconds
- **Total**: ~200-300 nanoseconds = 0.0003 milliseconds

**For 1,789 parameters**:
- Dict size has minimal impact on lookup time (O(1) average case)
- Worst case (collision): ~1-2 microseconds
- **Target**: 100 milliseconds
- **Actual**: 0.0003 milliseconds
- **Margin**: 333,000x faster than requirement

### Is Optimization Even Needed?

**NO.** The requirement is already exceeded by orders of magnitude.

**Evidence**:
- Target: <100ms
- Actual: <0.001ms (1 microsecond)
- **100,000x faster than requirement**

**Even the "slowest" approach (SQLite) is 100x faster than needed.**

---

## 4. Thread Safety Considerations

### Should Parameter Dict Be Immutable?

**YES.** Best practice: Make immutable after load.

**Rationale**:
1. Spec states single-threaded usage (no concurrency support)
2. Parameters are loaded once at startup from Feature 002
3. Preventing accidental modification is good defensive programming
4. No performance penalty for reads

### Implementation Options

#### Option 1: Types.MappingProxyType (Recommended)

```python
from types import MappingProxyType

class ParameterRegistry:
    def __init__(self, parameters):
        self._params = {
            param['text'].upper(): param
            for param in parameters
        }
        # Create read-only view
        self.params = MappingProxyType(self._params)

    def get(self, name, default=None):
        return self.params.get(name.upper(), default)
```

**Pros**:
- Built-in Python type (no dependencies)
- Truly immutable at Python level
- Zero performance overhead for reads
- Clear intent in code

**Cons**:
- Still possible to mutate via `_params` reference (convention-based protection)

---

#### Option 2: Frozen Dict (Python 3.9+)

Python 3.9+ has no built-in frozen dict, but MappingProxyType serves the same purpose.

---

#### Option 3: Convention-Based (Underscore Prefix)

```python
class ParameterRegistry:
    def __init__(self, parameters):
        # Convention: leading underscore = private, don't modify
        self._params = {
            param['text'].upper(): param
            for param in parameters
        }

    def get(self, name, default=None):
        return self._params.get(name.upper(), default)
```

**Pros**:
- Simplest approach
- Pythonic convention (leading underscore)
- No overhead

**Cons**:
- Not enforced - relies on programmer discipline
- Accidental modification still possible

---

### Thread Safety Best Practices

Even though spec says single-threaded:

1. **Make registry immutable after initialization**
   - Use `MappingProxyType` for public interface
   - Document that modification is not supported

2. **Document assumptions clearly**
   ```python
   class ParameterRegistry:
       """
       Parameter registry with case-insensitive lookup.

       Thread Safety:
       - Safe for concurrent reads (dict is read-only after init)
       - NOT safe for concurrent writes (not supported)
       - Assumes single-threaded sequential usage per spec
       """
   ```

3. **Design for defensive programming**
   - Return copies of mutable parameter data if needed
   - Or use frozen dataclasses for parameter objects

---

## 5. Recommendations

### Primary Recommendation ⭐

```python
from types import MappingProxyType
from typing import Optional, Dict, Any

class ParameterRegistry:
    """
    Case-insensitive parameter registry for Buderus WPS heat pump.

    Features:
    - O(1) lookup by parameter name
    - Case-insensitive access (internally normalized to uppercase)
    - Immutable after initialization
    - ~1 microsecond lookup time for 1,789 parameters

    Thread Safety:
    - Safe for concurrent reads
    - NOT safe for concurrent writes (not supported by design)
    """

    def __init__(self, parameters):
        """
        Initialize registry from parameter list.

        Args:
            parameters: List of dicts with keys: idx, extid, min, max,
                       format, read, text
        """
        # Normalize all keys to uppercase at load time
        self._params = {
            param['text'].upper(): param
            for param in parameters
        }
        # Create immutable view for public access
        self.params = MappingProxyType(self._params)

    def get(self, name: str, default: Optional[Any] = None) -> Optional[Dict]:
        """
        Get parameter by name (case-insensitive).

        Args:
            name: Parameter name (any case)
            default: Value to return if not found

        Returns:
            Parameter dict or default if not found
        """
        return self.params.get(name.upper(), default)

    def __getitem__(self, name: str) -> Dict:
        """Dict-like access (raises KeyError if not found)."""
        key = name.upper()
        if key not in self.params:
            raise KeyError(
                f"Parameter '{name}' not found. "
                f"Use .get() for optional lookup."
            )
        return self.params[key]

    def __contains__(self, name: str) -> bool:
        """Check if parameter exists (case-insensitive)."""
        return name.upper() in self.params

    def __len__(self) -> int:
        """Number of parameters."""
        return len(self.params)

    def keys(self):
        """All parameter names (uppercase)."""
        return self.params.keys()
```

### Usage Example

```python
# Initialize once at startup
params = load_parameters_from_fhem()  # Feature 002
registry = ParameterRegistry(params)

# Fast lookup (case-insensitive)
temp = registry.get("dhw_temp_setpoint")
alarm = registry.get("COMPRESSOR_ALARM")
level = registry.get("access_level")

# Check existence
if "DHW_TEMP_SETPOINT" in registry:
    print("Parameter exists")

# Dict-like access (raises KeyError if not found)
try:
    value = registry["invalid_param"]
except KeyError as e:
    print(f"Error: {e}")
```

---

## 6. Alternative Approaches Considered

### Summary Table

| Approach | Lookup Time | Memory | Complexity | Thread-Safe | Recommended |
|----------|-------------|--------|------------|-------------|-------------|
| Simple dict | 0.5-1.0 µs | 73 KB | Low | Yes (reads) | ⭐ **YES** |
| OrderedDict | 1.0-1.5 µs | 85 KB | Low | Yes (reads) | No benefit |
| Cached lookup | 0.5 µs | 146 KB | Medium | No | Overkill |
| SQLite | 100-500 µs | 300 KB | High | Yes | Massive overkill |
| Custom B-tree | 2-5 µs | 200 KB | Very High | Depends | Not needed |

---

## 7. Performance Estimates

### Lookup Performance (1,789 parameters)

```
Simple dict:              0.5-1.0 µs (microseconds)
OrderedDict:              1.0-1.5 µs
CaseInsensitiveDict:      0.8-1.2 µs
SQLite in-memory:       100-500 µs
Target requirement:   <100,000 µs (100 ms)

Conclusion: ANY approach meets requirement by 100,000x margin
```

### Memory Usage

```
Simple dict:        ~73 KB (dict) + ~350 KB (data) = ~423 KB total
OrderedDict:        ~85 KB (dict) + ~350 KB (data) = ~435 KB total
Cached approach:   ~146 KB (dicts) + ~350 KB (data) = ~496 KB total
SQLite:            ~300 KB (overhead) + data = ~650 KB total

Context: All approaches use <1 MB memory (completely negligible)
```

### Startup Time (Loading 1,789 Parameters)

```
Dict creation:        ~1-2 milliseconds
OrderedDict:          ~2-3 milliseconds
SQLite setup:        ~10-20 milliseconds

Conclusion: All approaches have negligible startup cost
```

---

## 8. Real-World Performance Testing Plan

While theoretical analysis shows dict is sufficient, here's how to validate:

```python
import timeit

def benchmark_lookup(registry, num_lookups=10000):
    """Benchmark parameter lookups."""
    params_to_test = [
        "ACCESS_LEVEL",
        "COMPRESSOR_ALARM",
        "DHW_TEMP_SETPOINT",
        "access_level",  # lowercase
        "Compressor_Alarm",  # mixed case
    ]

    def do_lookups():
        for _ in range(num_lookups // len(params_to_test)):
            for param in params_to_test:
                registry.get(param)

    time_taken = timeit.timeit(do_lookups, number=1)
    avg_per_lookup = (time_taken / num_lookups) * 1000000  # microseconds

    print(f"Average lookup time: {avg_per_lookup:.3f} µs")
    print(f"Target: <100,000 µs (100 ms)")
    print(f"Margin: {100000 / avg_per_lookup:.0f}x faster than required")

    return avg_per_lookup
```

Expected result: <1 microsecond average, >100,000x faster than requirement.

---

## 9. Conclusion

### Final Decision

**Use simple dict with uppercase keys and thin wrapper class.**

### Rationale Summary

1. **Performance**: Dict lookup is 100,000x faster than requirement (0.001ms vs 100ms)
2. **Simplicity**: <50 lines of code, easy to understand and maintain
3. **Memory**: <1 MB total (completely negligible)
4. **Thread Safety**: MappingProxyType provides immutability for reads
5. **Pythonic**: Idiomatic Python, follows stdlib patterns

### No Optimization Needed

The performance requirement (<100ms) is so loose that even the simplest approach exceeds it by 5 orders of magnitude. Any time spent optimizing beyond a simple dict would be premature optimization.

### Implementation Priority

1. ✅ Use simple dict with uppercase keys
2. ✅ Wrap in thin class for case-insensitive access
3. ✅ Make immutable with MappingProxyType
4. ✅ Add clear error messages for invalid lookups
5. ⚠️ Optional: Add "did you mean?" suggestions for typos (defer to later)

---

## References

- Python dict implementation: O(1) average case, O(n) worst case (rare)
- Hash table collision rate: <1% for good hash functions (Python's str hash is excellent)
- Feature 002 spec: Parameter definitions from FHEM source
- Feature 005 spec: NFR-005 requires <100ms lookup time
- Actual parameter count: 1,789 parameters from `/Users/rein/Documents/buderus-wps-ha/fhem/26_KM273v018.pm`
