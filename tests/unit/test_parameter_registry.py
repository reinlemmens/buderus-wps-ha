from buderus_wps.parameter_registry import ParameterRegistry


def test_registry_loads_defaults_and_lookup_by_name_and_index():
    registry = ParameterRegistry()
    # Ensure defaults loaded
    assert len(registry.parameters) > 1000

    access_level = registry.get_by_name("access_level")
    assert access_level is not None
    assert access_level.idx == 1

    idx_lookup = registry.get_by_index(1)
    assert idx_lookup is not None
    assert idx_lookup.text == access_level.text


def test_override_with_device_rebuilds_registry():
    device_entries = [
        {
            "idx": 10,
            "extid": "ABC",
            "max": 5,
            "min": 0,
            "format": "int",
            "read": 0,
            "text": "FOO",
        },
        {
            "idx": 11,
            "extid": "DEF",
            "max": 10,
            "min": 1,
            "format": "int",
            "read": 1,
            "text": "BAR",
        },
    ]
    registry = ParameterRegistry()
    registry.override_with_device(device_entries)

    assert registry.get_by_index(1) is None
    assert registry.get_by_name("FOO").idx == 10
    assert registry.get_by_name("bar").read == 1
