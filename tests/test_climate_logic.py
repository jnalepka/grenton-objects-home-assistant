import pytest
from custom_components.grenton_objects.climate import GrentonClimate
from homeassistant.components.climate import HVACMode
from tests.helpers import MockApiClient, MockHass


def create_obj(grenton_id="CLU220000000->THE0000", response_data=None, captured_command=None):
    if response_data is None:
        response_data = {"status": "ok"}
    api_client = MockApiClient(response_data=response_data, captured_command=captured_command)
    obj = GrentonClimate(
        api_endpoint="http://fake-api",
        grenton_id=grenton_id,
        object_name="Test obj",
        auto_update=False,
        update_interval=5,
        api_client=api_client
    )
    obj._initialized = True
    obj.hass = MockHass()
    obj.async_write_ha_state = lambda: None

    return obj

@pytest.mark.asyncio
async def test_async_set_temperature():
    captured_command = {}
    obj = create_obj(response_data={"status": "ok"}, captured_command=captured_command)
    await obj.async_set_temperature(temperature=20)

    assert captured_command["value"] == {
        "command": "CLU220000000:execute(0, 'THE0000:set(8, 0)')", "command_2": "CLU220000000:execute(0, 'THE0000:set(3, 20)')"
    }
    assert obj._target_temperature == 20
    assert obj._last_command_time == 123.456
    assert obj.unique_id == "grenton_THE0000"

@pytest.mark.asyncio
async def test_async_set_hvac_mode_heat():
    captured_command = {}
    obj = create_obj(response_data={"status": "ok"}, captured_command=captured_command)
    await obj.async_set_hvac_mode(HVACMode.HEAT)

    assert captured_command["value"] == {
        "command": "CLU220000000:execute(0, 'THE0000:execute(0, 0)')", "command_2": "CLU220000000:execute(0, 'THE0000:set(7, 0)')"
    }
    assert obj._last_command_time == 123.456
    assert obj.unique_id == "grenton_THE0000"
    assert obj._hvac_mode == HVACMode.HEAT

@pytest.mark.asyncio
async def test_async_set_hvac_mode_cool():
    captured_command = {}
    obj = create_obj(response_data={"status": "ok"}, captured_command=captured_command)
    await obj.async_set_hvac_mode(HVACMode.COOL)

    assert captured_command["value"] == {
        "command": "CLU220000000:execute(0, 'THE0000:execute(0, 0)')", "command_2": "CLU220000000:execute(0, 'THE0000:set(7, 1)')"
    }
    assert obj._last_command_time == 123.456
    assert obj.unique_id == "grenton_THE0000"
    assert obj._hvac_mode == HVACMode.COOL

@pytest.mark.asyncio
async def test_async_update():
    captured_command = {}
    obj = create_obj(response_data={"status": 1, "status_2": 1, "status_3": 22, "status_4": 19}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'THE0000:get(6)')", "status_2": "return CLU220000000:execute(0, 'THE0000:get(7)')", "status_3": "return CLU220000000:execute(0, 'THE0000:get(12)')", "status_4": "return CLU220000000:execute(0, 'THE0000:get(14)')"
    }
    assert obj._last_command_time is None
    assert obj.unique_id == "grenton_THE0000"
    assert obj._hvac_mode == HVACMode.COOL
    assert obj.target_temperature == 22
    assert obj.current_temperature == 19