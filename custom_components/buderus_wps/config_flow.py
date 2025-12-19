"""Config flow for Buderus WPS Heat Pump integration."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_SERIAL_DEVICE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class BuderusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Buderus WPS Heat Pump."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Test connection to heat pump
            try:
                await self.hass.async_add_executor_job(
                    self._test_connection, user_input[CONF_SERIAL_DEVICE]
                )
            except FileNotFoundError:
                errors["base"] = "device_not_found"
            except PermissionError:
                errors["base"] = "device_permission"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during connection test")
                errors["base"] = "cannot_connect"
            else:
                # Connection successful, create entry
                await self.async_set_unique_id(user_input[CONF_SERIAL_DEVICE])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Heat Pump ({user_input[CONF_SERIAL_DEVICE]})",
                    data=user_input,
                )

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_DEVICE, default="/dev/ttyACM0"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    def _test_connection(self, port: str) -> None:
        """Test connection to heat pump (runs in executor)."""
        from .buderus_wps.can_adapter import USBtinAdapter
        from .buderus_wps.heat_pump import HeatPumpClient

        # Try to initialize adapter
        adapter = USBtinAdapter(port, timeout=DEFAULT_TIMEOUT)
        adapter.connect()

        try:
            # Try to create client and ping the heat pump
            client = HeatPumpClient(adapter)
            # A simple connectivity test - just check if we can get the registry
            # This doesn't actually communicate with the heat pump yet
            _ = client.registry
        finally:
            adapter.disconnect()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BuderusOptionsFlow:
        """Get the options flow for this handler."""
        return BuderusOptionsFlow(config_entry)


class BuderusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Buderus WPS Heat Pump."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): cv.positive_int,
                }
            ),
        )
