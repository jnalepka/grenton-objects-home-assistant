"""
==================================================
Grenton API Client - Centralized HTTP communication layer
with shared session and optional request batching.

Repository: https://github.com/jnalepka/grenton-objects-home-assistant
==================================================
"""

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Default: single event-loop tick (asyncio.sleep(0)). Catches concurrent calls
# from HA group actions with zero perceptible delay for single commands.
DEFAULT_BATCH_WINDOW = 0.0


class GrentonApiError(Exception):
    """Normalized exception for non-aiohttp errors surfaced by the API client."""


class GrentonApiClient:
    """Centralized HTTP client for communicating with the Grenton HTTP Gate.

    Features:
    - Shared aiohttp.ClientSession (connection reuse, keepalive)
    - Command batching: collects commands within a configurable time window
      and merges them into a single HTTP request.

    Batch window behavior:
    - 0 (default): waits one event-loop tick (asyncio.sleep(0)). Only truly
      concurrent calls (e.g. HA group "turn off all lights") get batched.
      Single commands fire instantly with no perceptible delay.
    - >0: waits the specified seconds, collecting staggered commands.

    The user configures batch_window per integration entry. Entities sharing
    the same configuration/endpoint are batched together.
    """

    def __init__(self, endpoint: str, session: aiohttp.ClientSession, batch_window: float = DEFAULT_BATCH_WINDOW) -> None:
        self._endpoint = endpoint
        self._session = session
        self._batch_window = batch_window

        # Batching state
        self._pending_commands: list[tuple[str, asyncio.Future]] = []
        self._batch_lock = asyncio.Lock()
        self._batch_task: asyncio.Task | None = None

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def batch_window(self) -> float:
        return self._batch_window

    def _get_session(self) -> aiohttp.ClientSession:
        return self._session

    # ─── Public API ───────────────────────────────────────────────────────

    async def send_command(self, command: dict[str, str]) -> dict[str, Any]:
        """Send a command (POST) to the Grenton Gate.

        The command is queued and merged with other commands arriving within
        the batch window. With the default window of 0 (one event-loop tick),
        only truly concurrent calls (e.g. HA group actions) are batched —
        single commands fire with no perceptible delay.
        """
        futures: list[asyncio.Future] = []
        async with self._batch_lock:
            loop = asyncio.get_running_loop()
            for key, value in command.items():
                future: asyncio.Future = loop.create_future()
                self._pending_commands.append((value, future))
                futures.append(future)

            if self._batch_task is None or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._flush_batch())

        # Wait for the batch to be sent and return the merged response
        results = await asyncio.gather(*futures)
        # Reconstruct a response dict matching original keys
        response = {}
        for key, result in zip(command.keys(), results):
            response[key] = result
        return response

    async def get_status(self, query: dict[str, str]) -> dict[str, Any]:
        """Send a status query (GET) to the Grenton Gate.

        Status queries are not batched (each entity needs its own response
        at its own polling interval), but they reuse the shared session.
        """
        session = self._get_session()
        try:
            async with session.get(self._endpoint, json=query) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            raise
        except Exception as ex:
            raise GrentonApiError(str(ex)) from ex

    def close(self) -> None:
        """Cancel any in-flight batch task and fail pending futures.

        Called during unload to ensure no background work outlives the entry.
        """
        if self._batch_task and not self._batch_task.done():
            self._batch_task.cancel()
        for _, future in self._pending_commands:
            if not future.done():
                future.cancel()
        self._pending_commands.clear()

    # ─── Internal ─────────────────────────────────────────────────────────

    async def _flush_batch(self) -> None:
        """Wait for the batch window, then send all pending commands in one request.

        Drains in a loop to avoid a race where commands enqueued after the
        copy+clear but before the task completes would never be flushed.
        Re-applies the batch window before each cycle so late arrivals coalesce.
        """
        while True:
            await asyncio.sleep(self._batch_window)

            async with self._batch_lock:
                pending = self._pending_commands[:]
                self._pending_commands.clear()

            if not pending:
                # Re-check under lock to avoid lost-wakeup: a command may have
                # been enqueued after clear but before we reach this point, and
                # the enqueuer saw _batch_task as still running.
                async with self._batch_lock:
                    if self._pending_commands:
                        continue
                return

            # Build merged payload with numbered command keys
            payload: dict[str, str] = {}
            for i, (cmd_value, _) in enumerate(pending):
                key = "command" if i == 0 else f"command_{i + 1}"
                payload[key] = cmd_value

            # Send the single merged request
            try:
                session = self._get_session()
                async with session.post(self._endpoint, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()

                # Resolve all futures - the Grenton script returns results keyed
                # the same way we sent them
                for i, (_, future) in enumerate(pending):
                    key = "command" if i == 0 else f"command_{i + 1}"
                    result = data.get(key, data.get("g_status", "OK"))
                    if not future.done():
                        future.set_result(result)

            except asyncio.CancelledError:
                for _, future in pending:
                    if not future.done():
                        future.cancel()
                raise
            except Exception as ex:
                # On failure, reject all futures with a normalized exception
                wrapped = GrentonApiError(str(ex)) if not isinstance(ex, aiohttp.ClientError) else ex
                for _, future in pending:
                    if not future.done():
                        future.set_exception(wrapped)


def get_api_client(hass, endpoint: str, batch_window: float = DEFAULT_BATCH_WINDOW) -> GrentonApiClient:
    """Get or create a shared GrentonApiClient for the given endpoint.

    If a client already exists for this endpoint, returns the existing one.
    Uses Home Assistant's shared aiohttp session for proper connection management.
    """
    from .const import DOMAIN
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"entities": {}, "clients": {}}

    if "clients" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["clients"] = {}

    clients = hass.data[DOMAIN]["clients"]
    if endpoint not in clients:
        session = async_get_clientsession(hass)
        clients[endpoint] = GrentonApiClient(endpoint, session, batch_window=batch_window)

    return clients[endpoint]
