import pytest
from custom_components.grenton_objects.sensor import GrentonSensor
from tests.helpers import MockApiClient, MockHass


def create_obj(grenton_id="CLU220000000->DIN0000", grenton_type = "DEFAULT_SENSOR", unit_of_measurement = "°C", device_class = "temperature", state_class = "measurement", response_data=None, captured_command=None):
    if response_data is None:
        response_data = {"status": 1}
    api_client = MockApiClient(response_data=response_data, captured_command=captured_command)
    obj = GrentonSensor(
        api_endpoint="http://fake-api",
        grenton_id=grenton_id,
        grenton_type = grenton_type,
        object_name="Test Sensor",
        unit_of_measurement = unit_of_measurement,
        device_class = device_class,
        state_class = state_class,
        auto_update=False,
        update_interval=5,
        api_client=api_client
    )
    obj._initialized = True
    obj.hass = MockHass()
    obj.async_write_ha_state = lambda: None

    return obj

@pytest.mark.asyncio
async def test_async_update_panelsenstemp():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->PAN0000", grenton_type = "DEFAULT_SENSOR", unit_of_measurement = "°C", device_class = "temperature", state_class = "measurement", response_data={"status": 22.4}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'PAN0000:get(0)')"
    }
    assert obj.native_value == 22.4
    assert obj.native_unit_of_measurement == "°C"
    assert obj.device_class == "temperature"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_PAN0000"

@pytest.mark.asyncio
async def test_async_update_gate_feature():
    captured_command = {}
    obj = create_obj(grenton_id="my_feature_123", grenton_type = "DEFAULT_SENSOR", unit_of_measurement = "km/h", device_class = "wind_speed", state_class = "measurement", response_data={"status": 50.5}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return getVar(\"my_feature_123\")"
    }
    assert obj.native_value == 50.5
    assert obj.native_unit_of_measurement == "km/h"
    assert obj.device_class == "wind_speed"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_my_feature_123"

@pytest.mark.asyncio
async def test_async_update_clu_feature():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->my_feature_123", grenton_type = "DEFAULT_SENSOR", unit_of_measurement = "km/h", device_class = "wind_speed", state_class = "measurement", response_data={"status": 50.5}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'getVar(\"my_feature_123\")')"
    }
    assert obj.native_value == 50.5
    assert obj.native_unit_of_measurement == "km/h"
    assert obj.device_class == "wind_speed"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_my_feature_123"

@pytest.mark.asyncio
async def test_async_update_clu_feature_contain_obj_id():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->when_DOU1234_light_up", grenton_type = "DEFAULT_SENSOR", unit_of_measurement = "%", device_class = "humidity", state_class = "measurement", response_data={"status": 100}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'getVar(\"when_DOU1234_light_up\")')"
    }
    assert obj.native_value == 100
    assert obj.native_unit_of_measurement == "%"
    assert obj.device_class == "humidity"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_when_DOU1234_light_up"

@pytest.mark.asyncio
async def test_async_update_modbus():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->MOD0000", grenton_type = "MODBUS", unit_of_measurement = "kWh", device_class = "energy", state_class = "total", response_data={"status": 192349.12}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'MOD0000:get(14)')"
    }
    assert obj.native_value == 192349.12
    assert obj.native_unit_of_measurement == "kWh"
    assert obj.device_class == "energy"
    assert obj.state_class == "total"
    assert obj.unique_id == "grenton_MOD0000"

@pytest.mark.asyncio
async def test_async_update_modbus_value():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->MOD0000", grenton_type = "MODBUS_VALUE", unit_of_measurement = "kWh", device_class = "energy", state_class = "total_increasing", response_data={"status": 0.01}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'MOD0000:get(20)')"
    }
    assert obj.native_value == 0.01
    assert obj.native_unit_of_measurement == "kWh"
    assert obj.device_class == "energy"
    assert obj.state_class == "total_increasing"
    assert obj.unique_id == "grenton_MOD0000"

@pytest.mark.asyncio
async def test_async_update_modbus_rtu():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->MOD0000", grenton_type = "MODBUS_RTU", unit_of_measurement = "W", device_class = "power", state_class = "measurement", response_data={"status": 0.1}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'MOD0000:get(22)')"
    }
    assert obj.native_value == 0.1
    assert obj.native_unit_of_measurement == "W"
    assert obj.device_class == "power"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_MOD0000"

@pytest.mark.asyncio
async def test_async_update_modbus_client():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->MOD0000", grenton_type = "MODBUS_CLIENT", unit_of_measurement = None, device_class = "ph", state_class = "measurement", response_data={"status": 192349.12}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'MOD0000:get(19)')"
    }
    assert obj.native_value == 192349.12
    assert obj.native_unit_of_measurement is None
    assert obj.device_class == "ph"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_MOD0000"

@pytest.mark.asyncio
async def test_async_update_modbus_server():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->MOD0000", grenton_type = "MODBUS_SERVER", unit_of_measurement = "L", device_class = "water", state_class = "measurement", response_data={"status": 60}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'MOD0000:get(10)')"
    }
    assert obj.native_value == 60
    assert obj.native_unit_of_measurement == "L"
    assert obj.device_class == "water"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_MOD0000"

@pytest.mark.asyncio
async def test_async_update_modbus_slave_rtu():
    captured_command = {}
    obj = create_obj(grenton_id="CLU220000000->MOD0000", grenton_type = "MODBUS_SLAVE_RTU", unit_of_measurement = "ppb", device_class = "volatile_organic_compounds_parts", state_class = "measurement", response_data={"status": 401.1}, captured_command=captured_command)
    await obj.async_update()

    assert captured_command["value"] == {
        "status": "return CLU220000000:execute(0, 'MOD0000:get(10)')"
    }
    assert obj.native_value == 401.1
    assert obj.native_unit_of_measurement == "ppb"
    assert obj.device_class == "volatile_organic_compounds_parts"
    assert obj.state_class == "measurement"
    assert obj.unique_id == "grenton_MOD0000"