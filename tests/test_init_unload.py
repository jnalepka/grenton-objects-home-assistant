"""Tests for async_unload_entry client-cache eviction logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.grenton_objects import async_unload_entry
from custom_components.grenton_objects.const import DOMAIN, CONF_API_ENDPOINT


def _make_config_entry(entry_id, endpoint, device_type="switch"):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {
        "device_type": device_type,
        CONF_API_ENDPOINT: endpoint,
    }
    return entry


@pytest.mark.asyncio
async def test_client_removed_when_last_entry_unloaded():
    """Client is evicted from cache when the last entry using its endpoint is unloaded."""
    endpoint = "http://192.168.0.10:9999"
    entry = _make_config_entry("entry_1", endpoint)
    mock_client = MagicMock()

    hass = MagicMock()
    hass.data = {DOMAIN: {"entities": {}, "clients": {endpoint: mock_client}}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    # No remaining entries reference this endpoint
    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    result = await async_unload_entry(hass, entry)

    assert result is True
    assert endpoint not in hass.data[DOMAIN]["clients"]
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_client_retained_when_other_entry_shares_endpoint():
    """Client stays in cache when another config entry still references the same endpoint."""
    endpoint = "http://192.168.0.10:9999"
    entry_to_unload = _make_config_entry("entry_1", endpoint)
    other_entry = _make_config_entry("entry_2", endpoint)
    mock_client = MagicMock()

    hass = MagicMock()
    hass.data = {DOMAIN: {"entities": {}, "clients": {endpoint: mock_client}}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    # Another entry still uses the same endpoint
    hass.config_entries.async_entries = MagicMock(return_value=[entry_to_unload, other_entry])

    result = await async_unload_entry(hass, entry_to_unload)

    assert result is True
    assert endpoint in hass.data[DOMAIN]["clients"]
    assert hass.data[DOMAIN]["clients"][endpoint] is mock_client
