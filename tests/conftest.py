"""Shared fixtures for Big Sky Resort tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.big_sky.const import (
    CONF_CREATE_LIFT_ENTITIES,
    CONF_CREATE_RUN_ENTITIES,
    CONF_FEED_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FEED_URL,
    DOMAIN,
)

FIXTURE = Path(__file__).parent / "fixtures" / "feed_162.xml"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/ in every test."""
    return


@pytest.fixture(autouse=True)
def us_units(hass):
    """The feed is in US units; keep test states in the same units."""
    hass.config.units = US_CUSTOMARY_SYSTEM


@pytest.fixture
def feed_xml() -> str:
    return FIXTURE.read_text()


@pytest.fixture
def mock_feed(aioclient_mock: AiohttpClientMocker, feed_xml: str) -> AiohttpClientMocker:
    aioclient_mock.get(DEFAULT_FEED_URL, text=feed_xml)
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Big Sky Resort",
        version=2,
        unique_id=DOMAIN,
        data={
            CONF_FEED_URL: DEFAULT_FEED_URL,
            CONF_CREATE_LIFT_ENTITIES: True,
            CONF_CREATE_RUN_ENTITIES: True,
            CONF_UPDATE_INTERVAL: 15,
        },
    )
