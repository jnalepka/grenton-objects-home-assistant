"""Tests for GrentonApiClient command batching logic."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.grenton_objects.api import GrentonApiClient, GrentonApiError


def _make_mock_session(response_data):
    """Create a mock aiohttp session with a preconfigured POST response."""
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value=response_data)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)
    return mock_session


@pytest.mark.asyncio
async def test_single_command_sends_one_post():
    """A single send_command should result in exactly one POST with key 'command'."""
    mock_session = _make_mock_session({"command": "OK"})
    client = GrentonApiClient("http://fake-gate", mock_session, batch_window=0.0)

    result = await client.send_command({"command": "CLU:execute(0, 'DOU:set(0, 1)')"})

    assert result == {"command": "OK"}
    mock_session.post.assert_called_once()
    payload = mock_session.post.call_args[1]["json"]
    assert payload == {"command": "CLU:execute(0, 'DOU:set(0, 1)')"}


@pytest.mark.asyncio
async def test_concurrent_commands_batched_into_single_post():
    """Multiple send_command calls in the same tick should merge into one POST."""
    mock_session = _make_mock_session({
        "command": "result_1",
        "command_2": "result_2",
        "command_3": "result_3",
    })
    client = GrentonApiClient("http://fake-gate", mock_session, batch_window=0.0)

    # Fire three commands concurrently (same event-loop tick)
    results = await asyncio.gather(
        client.send_command({"command": "cmd_a"}),
        client.send_command({"command": "cmd_b"}),
        client.send_command({"command": "cmd_c"}),
    )

    # Should have been a single POST
    assert mock_session.post.call_count == 1
    payload = mock_session.post.call_args[1]["json"]
    # Payload should contain command, command_2, command_3
    assert "command" in payload
    assert "command_2" in payload
    assert "command_3" in payload

    # Each caller gets its correct result
    assert results[0] == {"command": "result_1"}
    assert results[1] == {"command": "result_2"}
    assert results[2] == {"command": "result_3"}


@pytest.mark.asyncio
async def test_multi_key_command_batched_correctly():
    """A command dict with multiple keys should generate sequential numbered keys."""
    mock_session = _make_mock_session({
        "command": "res_a",
        "command_2": "res_b",
    })
    client = GrentonApiClient("http://fake-gate", mock_session, batch_window=0.0)

    result = await client.send_command({
        "command": "set_temp",
        "command_2": "set_mode",
    })

    assert result == {"command": "res_a", "command_2": "res_b"}
    payload = mock_session.post.call_args[1]["json"]
    assert payload == {"command": "set_temp", "command_2": "set_mode"}


@pytest.mark.asyncio
async def test_failure_rejects_all_futures_with_grenton_api_error():
    """When POST fails with a non-aiohttp error, futures get GrentonApiError."""
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(side_effect=ValueError("bad json"))
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)

    client = GrentonApiClient("http://fake-gate", mock_session, batch_window=0.0)

    with pytest.raises(GrentonApiError):
        await client.send_command({"command": "some_cmd"})


@pytest.mark.asyncio
async def test_batch_window_coalesces_staggered_commands():
    """With a non-zero batch window, commands arriving within it are merged."""
    mock_session = _make_mock_session({
        "command": "r1",
        "command_2": "r2",
    })
    client = GrentonApiClient("http://fake-gate", mock_session, batch_window=0.05)

    # Send first command
    task1 = asyncio.create_task(client.send_command({"command": "cmd_1"}))
    # Small delay then send second (within batch window)
    await asyncio.sleep(0.01)
    task2 = asyncio.create_task(client.send_command({"command": "cmd_2"}))

    results = await asyncio.gather(task1, task2)

    # Both should be in a single POST
    assert mock_session.post.call_count == 1
    assert results[0] == {"command": "r1"}
    assert results[1] == {"command": "r2"}
