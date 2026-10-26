"""Config and options flow tests."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.big_sky.const import (
    CONF_CREATE_LIFT_ENTITIES,
    CONF_CREATE_RUN_ENTITIES,
    CONF_FEED_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FEED_URL,
    DOMAIN,
)

USER_INPUT = {
    CONF_FEED_URL: DEFAULT_FEED_URL,
    CONF_CREATE_LIFT_ENTITIES: True,
    CONF_CREATE_RUN_ENTITIES: False,
    CONF_UPDATE_INTERVAL: 30,
}


async def test_user_flow_success(hass: HomeAssistant, mock_feed) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Big Sky Resort"
    assert result["data"] == USER_INPUT


async def test_user_flow_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(DEFAULT_FEED_URL, status=503)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_not_xml(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(DEFAULT_FEED_URL, text="<html><body>maintenance")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_rejects_http(hass: HomeAssistant, aioclient_mock) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**USER_INPUT, CONF_FEED_URL: "http://reportpal-cdn.resorts-interactive.com/mtnxml/162"},
    )
    assert result["errors"] == {CONF_FEED_URL: "https_required"}
    assert aioclient_mock.call_count == 0


async def test_user_flow_rejects_oversize(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(DEFAULT_FEED_URL, text="<report>" + "x" * (3 * 1024 * 1024))
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "feed_too_large"}


async def test_single_instance(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow_updates_options(
    hass: HomeAssistant, mock_feed, config_entry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_FEED_URL: DEFAULT_FEED_URL,
            CONF_CREATE_LIFT_ENTITIES: True,
            CONF_CREATE_RUN_ENTITIES: False,
            CONF_UPDATE_INTERVAL: 60,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options[CONF_UPDATE_INTERVAL] == 60
    # The reload reads options over data, so trail entities are gone.
    assert hass.states.get("binary_sensor.big_sky_resort_trail_little_thunder") is None
    assert config_entry.runtime_data.update_interval.total_seconds() == 3600
