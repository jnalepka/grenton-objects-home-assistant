import pytest
from custom_components.grenton_objects.button import GrentonScript
from tests.helpers import MockApiClient, MockHass


def create_obj(grenton_id="my_script", response_data=None, captured_command=None):
    if response_data is None:
        response_data = {"status": "ok"}
    api_client = MockApiClient(response_data=response_data, captured_command=captured_command)
    obj = GrentonScript(
        api_endpoint="http://fake-api",
        grenton_id=grenton_id,
        object_name="Test Script",
        api_client=api_client
    )
    obj.hass = MockHass()
    obj.async_write_ha_state = lambda: None

    return obj

@pytest.mark.asyncio
async def test_async_script_local():
    captured_command = {}
    obj = create_obj(response_data={"status": "ok"}, captured_command=captured_command)
    await obj.async_press()

    assert captured_command["value"] == {
        "command": "my_script(nil)"
    }
    assert obj.unique_id == "grenton_my_script"

@pytest.mark.asyncio
async def test_async_script_remote():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->my_script_2", response_data={"status": "ok"}, captured_command=captured_command)
    await obj.async_press()

    assert captured_command["value"] == {
        "command": "CLU220000000:execute(0, 'my_script_2(nil)')"
    }
    assert obj.unique_id == "grenton_my_script_2"