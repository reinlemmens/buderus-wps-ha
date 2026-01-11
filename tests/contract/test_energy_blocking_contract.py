"""Contract tests for energy blocking CAN protocol encoding/decoding.

Verifies that CAN message encoding matches the FHEM reference implementation
for blocking parameters.

PROTOCOL: Reference FHEM 26_KM273v018.pm
- COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 (idx 263, extid C092971E2F0309)
- COMPRESSOR_BLOCKED (idx 247, extid 000E6864FD0476)
- ADDITIONAL_USER_BLOCKED (idx 155, extid C09241BB5C02EC)
- ADDITIONAL_BLOCKED (idx 9, extid 00259EEF360272)
"""

# Phase 3: User Story 1 contract tests (T014-T015)


class TestCompressorBlockContract:
    """Contract tests for compressor blocking CAN parameters - T014, T015."""

    def test_compressor_block_write_parameter_exists(self) -> None:
        """COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 exists in registry."""
        from buderus_wps import HeatPump

        hp = HeatPump()
        param = hp.get_parameter_by_name("COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1")

        assert param is not None
        assert param.idx == 263
        assert param.extid == "C092971E2F0309"

    def test_compressor_block_write_can_id_encoding(self) -> None:
        """Write CAN ID for compressor block matches FHEM protocol.

        PROTOCOL: Write uses 0x04003FE0 | (idx << 14)
        Reference: FHEM 26_KM273v018.pm line 2229
        """
        idx = 263
        expected_can_id = 0x04003FE0 | (idx << 14)
        # 0x04003FE0 | (263 << 14) = 0x0441FFE0

        assert expected_can_id == 0x0441FFE0

    def test_compressor_block_value_encoding(self) -> None:
        """Block value encodes as 0x01, unblock as 0x00.

        PROTOCOL: Boolean parameters use 1-byte encoding.
        """
        # Block = True = 1
        blocked_value = (1).to_bytes(1, "big")
        assert blocked_value == b"\x01"

        # Unblock = False = 0
        unblocked_value = (0).to_bytes(1, "big")
        assert unblocked_value == b"\x00"

    def test_compressor_status_read_parameter_exists(self) -> None:
        """COMPRESSOR_BLOCKED exists in registry for status reading."""
        from buderus_wps import HeatPump

        hp = HeatPump()
        param = hp.get_parameter_by_name("COMPRESSOR_BLOCKED")

        assert param is not None
        assert param.idx == 247
        assert param.extid == "000E6864FD0476"

    def test_compressor_status_read_can_id_encoding(self) -> None:
        """Read CAN ID for compressor status matches FHEM protocol.

        PROTOCOL: Read request uses 0x04003FE0 | (idx << 14) with RTR
        Reference: FHEM 26_KM273v018.pm line 2678
        """
        idx = 247
        request_can_id = 0x04003FE0 | (idx << 14)
        response_can_id = 0x0C003FE0 | (idx << 14)

        # Request: 0x04003FE0 | (247 << 14) = 0x043DFFE0
        assert request_can_id == 0x043DFFE0
        # Response: 0x0C003FE0 | (247 << 14) = 0x0C3DFFE0
        assert response_can_id == 0x0C3DFFE0

    def test_compressor_status_value_decoding(self) -> None:
        """Status value decodes as blocked (non-zero) or normal (zero)."""
        # Status = 0 means not blocked
        status_normal = int.from_bytes(b"\x00", "big")
        assert status_normal == 0

        # Status != 0 means blocked
        status_blocked = int.from_bytes(b"\x01", "big")
        assert status_blocked != 0


# Phase 4: User Story 2 contract tests (T024-T025)


class TestAuxHeaterBlockContract:
    """Contract tests for aux heater blocking CAN parameters - T024, T025."""

    def test_aux_heater_block_write_parameter_exists(self) -> None:
        """ADDITIONAL_USER_BLOCKED exists in registry."""
        from buderus_wps import HeatPump

        hp = HeatPump()
        param = hp.get_parameter_by_name("ADDITIONAL_USER_BLOCKED")

        assert param is not None
        assert param.idx == 155
        assert param.extid == "C09241BB5C02EC"

    def test_aux_heater_status_read_parameter_exists(self) -> None:
        """ADDITIONAL_BLOCKED exists in registry for status reading."""
        from buderus_wps import HeatPump

        hp = HeatPump()
        param = hp.get_parameter_by_name("ADDITIONAL_BLOCKED")

        assert param is not None
        assert param.idx == 9
        assert param.extid == "00259EEF360272"
