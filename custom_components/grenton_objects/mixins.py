"""Shared mixins for Grenton Objects entity classes."""

from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval

from .const import COMMAND_DEBOUNCE_SECONDS


def is_within_debounce(last_command_time, hass) -> bool:
    """Return True if a command was sent recently and poll results should be ignored."""
    if last_command_time is None:
        return False
    if hass is None or not hasattr(hass, 'loop') or hass.loop is None:
        return False
    if not callable(getattr(hass.loop, 'time', None)):
        return False
    return hass.loop.time() - last_command_time < COMMAND_DEBOUNCE_SECONDS
    

class GrentonPollingMixin:
    """Mixin providing auto-update polling lifecycle for Grenton entities.

    Expects the entity to define:
        _auto_update: bool
        _update_interval: int (seconds)
        _initialized: bool (initially False)
        _unsub_interval: callable | None (initially None)
        async_update(): coroutine
    """

    async def async_added_to_hass(self):
        self._initialized = True
        if self._auto_update:
            self._unsub_interval = async_track_time_interval(
                self.hass, self._update_callback, timedelta(seconds=self._update_interval)
            )
            await self.async_update()

    async def async_will_remove_from_hass(self):
        if self._unsub_interval:
            self._unsub_interval()

    async def _update_callback(self, now):
        await self.async_update()
