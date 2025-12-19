import sys
print(sys.version)
d = {f'P_{i}': i for i in range(1789)}
print(f"Dict size: {sys.getsizeof(d)} bytes")
print(f"Lookup test: {d.get('P_1788')}")
