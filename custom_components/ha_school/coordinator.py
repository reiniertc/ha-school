from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MagisterApiClient
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HaSchoolCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: MagisterApiClient, update_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval or DEFAULT_UPDATE_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self):
        try:
            return await self.client.async_fetch_all()
        except Exception as err:
            raise UpdateFailed(f"Update mislukt: {err}") from err
