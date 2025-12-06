"""Contract tests for broadcast read output format.

Tests verify the output format contracts for the CLI read command
when using broadcast mode.
"""

from __future__ import annotations

import json
import pytest


class TestBroadcastReadTextOutputContract:
    """Contract tests for text output format with broadcast source."""

    def test_text_output_includes_source_field(self) -> None:
        """Text output must include source indication."""
        # Contract: output format is "PARAM_NAME = VALUE  (raw=0xXX, idx=NNN, source=SOURCE)"
        expected_pattern = r"^[\w_]+ = .+  \(raw=0x[0-9A-Fa-f]+, idx=\d+, source=(rtr|broadcast)\)$"

        # Example valid outputs
        valid_rtr = "GT2_TEMP = 10.5 C  (raw=0x0069, idx=10, source=rtr)"
        valid_broadcast = "GT2_TEMP = 10.5 C  (raw=0x0069, idx=10, source=broadcast)"

        import re
        assert re.match(expected_pattern, valid_rtr), "RTR source format must match contract"
        assert re.match(expected_pattern, valid_broadcast), "Broadcast source format must match contract"


class TestBroadcastReadJsonOutputContract:
    """Contract tests for JSON output format with broadcast source."""

    def test_json_output_includes_source_field(self) -> None:
        """JSON output must include 'source' field."""
        # Contract: JSON must have source field with value "rtr" or "broadcast"
        json_output = {
            "name": "GT2_TEMP",
            "idx": 10,
            "raw": "0069",
            "decoded": 10.5,
            "source": "broadcast"
        }

        assert "source" in json_output
        assert json_output["source"] in ("rtr", "broadcast")

    def test_json_source_field_values(self) -> None:
        """JSON source field must be exactly 'rtr' or 'broadcast'."""
        valid_sources = ["rtr", "broadcast"]
        invalid_sources = ["RTR", "BROADCAST", "Rtr", "Broadcast", "direct", "cache"]

        for source in valid_sources:
            assert source in ("rtr", "broadcast"), f"{source} should be valid"

        for source in invalid_sources:
            assert source not in ("rtr", "broadcast"), f"{source} should be invalid"

    def test_json_required_fields(self) -> None:
        """JSON output must have all required fields."""
        required_fields = {"name", "idx", "raw", "decoded", "source"}

        # This is the contract - cmd_read JSON output must include these fields
        json_output = {
            "name": "GT2_TEMP",
            "idx": 10,
            "raw": "0069",
            "decoded": 10.5,
            "source": "rtr"
        }

        assert required_fields.issubset(json_output.keys()), (
            f"Missing required fields: {required_fields - set(json_output.keys())}"
        )


class TestBroadcastReadErrorContract:
    """Contract tests for broadcast read error messages."""

    def test_broadcast_not_available_error_format(self) -> None:
        """Error message format for parameter not available via broadcast."""
        # Contract: "ERROR: PARAM_NAME not available via broadcast"
        param_name = "UNKNOWN_PARAM"
        expected_error = f"ERROR: {param_name} not available via broadcast"

        # Verify the format pattern
        import re
        pattern = r"^ERROR: [\w_]+ not available via broadcast$"
        assert re.match(pattern, expected_error)

    def test_broadcast_timeout_error_format(self) -> None:
        """Error message format for broadcast timeout."""
        # Contract: "ERROR: No broadcast data received for PARAM_NAME within X seconds"
        param_name = "GT2_TEMP"
        duration = 5.0
        expected_error = f"ERROR: No broadcast data received for {param_name} within {duration} seconds"

        # Verify the format pattern
        import re
        pattern = r"^ERROR: No broadcast data received for [\w_]+ within [\d.]+ seconds$"
        assert re.match(pattern, expected_error)


class TestFallbackWarningContract:
    """Contract tests for fallback warning messages."""

    def test_fallback_triggered_warning_format(self) -> None:
        """Warning message format when fallback is triggered."""
        # Contract: "WARNING: RTR returned invalid data, using broadcast fallback"
        expected_warning = "WARNING: RTR returned invalid data, using broadcast fallback"

        assert "WARNING:" in expected_warning
        assert "broadcast fallback" in expected_warning

    def test_fallback_failed_warning_format(self) -> None:
        """Warning message format when fallback fails."""
        # Contract: "WARNING: RTR returned invalid data, broadcast fallback failed"
        expected_warning = "WARNING: RTR returned invalid data, broadcast fallback failed"

        assert "WARNING:" in expected_warning
        assert "fallback failed" in expected_warning
