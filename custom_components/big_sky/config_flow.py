"""Config flow for Big Sky Resort integration."""
from __future__ import annotations
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_FEED_URL,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    CONF_FEED_URL,
    CONF_CREATE_RUN_ENTITIES,
    CONF_CREATE_LIFT_ENTITIES,
    CONF_UPDATE_INTERVAL,
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # TODO: Add API URL validation
    return {"title": "Big Sky Resort"}

class BigSkyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Big Sky Resort."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_FEED_URL, default=DEFAULT_FEED_URL): cv.string,
                    vol.Required(CONF_CREATE_LIFT_ENTITIES, default=True): cv.boolean,
                    vol.Required(CONF_CREATE_RUN_ENTITIES, default=True): cv.boolean,
                    vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
                    ),
                })
            )

        return self.async_create_entry(
            title="Big Sky Resort",
            data=user_input
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> BigSkyOptionsFlow:
        """Get the options flow."""
        return BigSkyOptionsFlow(config_entry)

class BigSkyOptionsFlow(config_entries.OptionsFlow):
    """Handle Big Sky Resort options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_FEED_URL,
                    default=self.config_entry.data.get(CONF_FEED_URL, DEFAULT_FEED_URL),
                ): cv.string,
                vol.Required(
                    CONF_CREATE_LIFT_ENTITIES,
                    default=self.config_entry.data.get(CONF_CREATE_LIFT_ENTITIES, True),
                ): cv.boolean,
                vol.Required(
                    CONF_CREATE_RUN_ENTITIES,
                    default=self.config_entry.data.get(CONF_CREATE_RUN_ENTITIES, True),
                ): cv.boolean,
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
                ),
            })
        )