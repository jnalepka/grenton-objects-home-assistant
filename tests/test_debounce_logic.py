"""Tests for debounce utility and race guard logic."""

import pytest
from custom_components.grenton_objects.mixins import is_within_debounce
from custom_components.grenton_objects.const import (
    COMMAND_DEBOUNCE_SECONDS,
    CONF_GRENTON_TYPE_DOUT,
)
from custom_components.grenton_objects.switch import GrentonSwitch
from custom_components.grenton_objects.light import GrentonLight
from custom_components.grenton_objects.cover import GrentonCover
from custom_components.grenton_objects.climate import GrentonClimate
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.climate import HVACMode
from tests.helpers import MockApiClient


class MockHassWithTime:
    """MockHass with configurable loop time."""

    def __init__(self, current_time=100.0):
        self._time = current_time
        self.loop = self

    def time(self):
        return self._time

    def set_time(self, t):
        self._time = t


# --- is_within_debounce tests ---


def test_is_within_debounce_no_command():
    """Should return False when no command has been sent."""
    hass = MockHassWithTime()
    assert is_within_debounce(None, hass) is False


def test_is_within_debounce_recent_command():
    """Should return True when command was sent less than COMMAND_DEBOUNCE_SECONDS ago."""
    hass = MockHassWithTime(current_time=100.0)
    last_command_time = 99.5  # 0.5s ago
    assert is_within_debounce(last_command_time, hass) is True


def test_is_within_debounce_old_command():
    """Should return False when command was sent more than COMMAND_DEBOUNCE_SECONDS ago."""
    hass = MockHassWithTime(current_time=100.0)
    last_command_time = 97.0  # 3s ago
    assert is_within_debounce(last_command_time, hass) is False


def test_is_within_debounce_exactly_at_boundary():
    """Should return False when exactly at the debounce boundary."""
    hass = MockHassWithTime(current_time=100.0)
    last_command_time = 100.0 - COMMAND_DEBOUNCE_SECONDS
    assert is_within_debounce(last_command_time, hass) is False


# --- Race guard tests ---


def create_switch(response_data=None, current_time=100.0):
    if response_data is None:
        response_data = {"status": 0}
    api_client = MockApiClient(response_data=response_data)
    obj = GrentonSwitch(
        api_endpoint="http://fake-api",
        grenton_id="CLU220000000->DOU0000",
        object_name="Test Switch",
        auto_update=False,
        update_interval=5,
        api_client=api_client,
    )
    obj._initialized = True
    obj.hass = MockHassWithTime(current_time)
    obj.async_write_ha_state = lambda: None
    return obj


@pytest.mark.asyncio
async def test_race_guard_skips_update_during_debounce():
    """async_update should skip when within debounce window."""
    obj = create_switch(response_data={"status": 0}, current_time=100.0)
    # Simulate a command was just sent
    obj._state = STATE_ON
    obj._last_command_time = 99.5  # 0.5s ago

    await obj.async_update()

    # State should NOT be overwritten by the poll (which returns status=0 → OFF)
    assert obj._state == STATE_ON


@pytest.mark.asyncio
async def test_race_guard_allows_update_after_debounce():
    """async_update should proceed when debounce window has passed."""
    obj = create_switch(response_data={"status": 0}, current_time=100.0)
    # Simulate a command sent long ago
    obj._state = STATE_ON
    obj._last_command_time = 97.0  # 3s ago

    await obj.async_update()

    # State should be updated from the poll response
    assert obj._state == STATE_OFF


@pytest.mark.asyncio
async def test_race_guard_post_await_check():
    """If a command fires while HTTP is in-flight, result should be discarded."""
    obj = create_switch(response_data={"status": 0}, current_time=100.0)
    obj._last_command_time = None  # no recent command at start

    # Monkey-patch the api_client to simulate a command firing during the HTTP call
    original_get_status = obj._api_client.get_status

    async def get_status_with_side_effect(query):
        # Simulate: while waiting for HTTP response, a command was issued
        obj._last_command_time = 100.0  # command fires "now"
        return await original_get_status(query)

    obj._api_client.get_status = get_status_with_side_effect

    obj._state = STATE_ON  # optimistic state from the simulated command
    await obj.async_update()

    # The stale poll result (status=0 → OFF) should be discarded
    assert obj._state == STATE_ON


# --- Light race guard tests ---


def create_light(response_data=None, current_time=100.0):
    if response_data is None:
        response_data = {"status": 0}
    api_client = MockApiClient(response_data=response_data)
    obj = GrentonLight(
        api_endpoint="http://fake-api",
        grenton_id="CLU220000000->DOU0000",
        grenton_type=CONF_GRENTON_TYPE_DOUT,
        object_name="Test Light",
        auto_update=False,
        update_interval=5,
        api_client=api_client,
    )
    obj._initialized = True
    obj.hass = MockHassWithTime(current_time)
    obj.async_write_ha_state = lambda: None
    return obj


@pytest.mark.asyncio
async def test_light_race_guard_skips_update_during_debounce():
    """Light async_update should skip when within debounce window."""
    obj = create_light(response_data={"status": 0}, current_time=100.0)
    obj._state = STATE_ON
    obj._last_command_time = 99.5

    await obj.async_update()

    assert obj._state == STATE_ON


@pytest.mark.asyncio
async def test_light_race_guard_post_await_check():
    """If a command fires while light HTTP is in-flight, result should be discarded."""
    obj = create_light(response_data={"status": 0}, current_time=100.0)
    obj._last_command_time = None

    original_get_status = obj._api_client.get_status

    async def get_status_with_side_effect(query):
        obj._last_command_time = 100.0
        return await original_get_status(query)

    obj._api_client.get_status = get_status_with_side_effect
    obj._state = STATE_ON
    await obj.async_update()

    assert obj._state == STATE_ON


# --- Cover race guard tests ---


def create_cover(response_data=None, current_time=100.0):
    if response_data is None:
        response_data = {"status": 0, "status_2": 50, "status_3": 0}
    api_client = MockApiClient(response_data=response_data)
    obj = GrentonCover(
        api_endpoint="http://fake-api",
        grenton_id="CLU220000000->ROL0000",
        reversed=False,
        object_name="Test Cover",
        auto_update=False,
        update_interval=5,
        device_class="blind",
        api_client=api_client,
    )
    obj._initialized = True
    obj.hass = MockHassWithTime(current_time)
    obj.async_write_ha_state = lambda: None
    return obj


@pytest.mark.asyncio
async def test_cover_race_guard_skips_update_during_debounce():
    """Cover async_update should skip when within debounce window."""
    from homeassistant.const import STATE_OPEN
    obj = create_cover(response_data={"status": 0, "status_2": 0, "status_3": 0}, current_time=100.0)
    obj._state = STATE_OPEN
    obj._current_cover_position = 100
    obj._last_command_time = 99.5

    await obj.async_update()

    assert obj._state == STATE_OPEN
    assert obj._current_cover_position == 100


@pytest.mark.asyncio
async def test_cover_race_guard_post_await_check():
    """If a command fires while cover HTTP is in-flight, result should be discarded."""
    from homeassistant.const import STATE_OPEN
    obj = create_cover(response_data={"status": 0, "status_2": 0, "status_3": 0}, current_time=100.0)
    obj._last_command_time = None

    original_get_status = obj._api_client.get_status

    async def get_status_with_side_effect(query):
        obj._last_command_time = 100.0
        return await original_get_status(query)

    obj._api_client.get_status = get_status_with_side_effect
    obj._state = STATE_OPEN
    obj._current_cover_position = 100
    await obj.async_update()

    assert obj._state == STATE_OPEN
    assert obj._current_cover_position == 100


# --- Climate race guard tests ---


def create_climate(response_data=None, current_time=100.0):
    if response_data is None:
        response_data = {"status": 1, "status_2": 0, "status_3": 22.0, "status_4": 20.0}
    api_client = MockApiClient(response_data=response_data)
    obj = GrentonClimate(
        api_endpoint="http://fake-api",
        grenton_id="CLU220000000->THE0000",
        object_name="Test Climate",
        auto_update=False,
        update_interval=5,
        api_client=api_client,
    )
    obj._initialized = True
    obj.hass = MockHassWithTime(current_time)
    obj.async_write_ha_state = lambda: None
    return obj


@pytest.mark.asyncio
async def test_climate_race_guard_skips_update_during_debounce():
    """Climate async_update should skip when within debounce window."""
    # Response would set HEAT mode, but debounce should prevent update
    obj = create_climate(
        response_data={"status": 1, "status_2": 0, "status_3": 25.0, "status_4": 21.0},
        current_time=100.0,
    )
    obj._hvac_mode = HVACMode.OFF
    obj._target_temperature = 20.0
    obj._last_command_time = 99.5

    await obj.async_update()

    assert obj._hvac_mode == HVACMode.OFF
    assert obj._target_temperature == 20.0


@pytest.mark.asyncio
async def test_climate_race_guard_post_await_check():
    """If a command fires while climate HTTP is in-flight, result should be discarded."""
    obj = create_climate(
        response_data={"status": 1, "status_2": 0, "status_3": 25.0, "status_4": 21.0},
        current_time=100.0,
    )
    obj._last_command_time = None

    original_get_status = obj._api_client.get_status

    async def get_status_with_side_effect(query):
        obj._last_command_time = 100.0
        return await original_get_status(query)

    obj._api_client.get_status = get_status_with_side_effect
    obj._hvac_mode = HVACMode.OFF
    obj._target_temperature = 20.0
    await obj.async_update()

    assert obj._hvac_mode == HVACMode.OFF
    assert obj._target_temperature == 20.0
