"""Config flow for Big Sky Resort."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_CREATE_LIFT_ENTITIES,
    CONF_CREATE_RUN_ENTITIES,
    CONF_FEED_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FEED_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    NAME,
)
from .feed import FeedError, FeedTooLarge, fetch_feed

_LOGGER = logging.getLogger(__name__)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_FEED_URL, default=defaults.get(CONF_FEED_URL, DEFAULT_FEED_URL)
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
            vol.Required(
                CONF_CREATE_LIFT_ENTITIES,
                default=defaults.get(CONF_CREATE_LIFT_ENTITIES, True),
            ): bool,
            vol.Required(
                CONF_CREATE_RUN_ENTITIES,
                default=defaults.get(CONF_CREATE_RUN_ENTITIES, True),
            ): bool,
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=max(
                    MIN_UPDATE_INTERVAL,
                    min(
                        MAX_UPDATE_INTERVAL,
                        int(defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
                    ),
                ),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL,
                        max=MAX_UPDATE_INTERVAL,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Coerce(int),
            ),
        }
    )


async def validate_feed(hass: HomeAssistant, user_input: dict[str, Any]) -> dict[str, str]:
    """Check the URL and try one fetch. Returns form errors, empty on success."""
    url = str(user_input.get(CONF_FEED_URL, "")).strip()
    try:
        cv.url(url)
    except vol.Invalid:
        return {CONF_FEED_URL: "invalid_url"}
    if urlparse(url).scheme != "https":
        return {CONF_FEED_URL: "https_required"}
    user_input[CONF_FEED_URL] = url
    try:
        await fetch_feed(async_get_clientsession(hass), url)
    except FeedTooLarge:
        return {"base": "feed_too_large"}
    except FeedError as err:
        _LOGGER.debug("Feed check failed for %s: %s", url, err)
        return {"base": "cannot_connect"}
    return {}


class BigSkyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Big Sky Resort from the UI."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            errors = await validate_feed(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_schema({}), user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BigSkyOptionsFlow:
        return BigSkyOptionsFlow()


class BigSkyOptionsFlow(OptionsFlow):
    """Change feed URL, entity choices and polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            # Only re-check the feed when the URL changes, so a feed outage
            # does not block changing the interval.
            if user_input.get(CONF_FEED_URL) != current.get(CONF_FEED_URL):
                errors = await validate_feed(self.hass, user_input)
            if not errors:
                return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(_schema(current), user_input),
            errors=errors,
        )
