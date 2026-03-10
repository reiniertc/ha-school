from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import MagisterApiClient
from .coordinator import HaSchoolCoordinator
from .const import (
    CONF_PASSWORD,
    CONF_SCHOOL,
    CONF_STUDENT_ID,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    CONF_WEEKS_AHEAD,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WEEKS_AHEAD,
    DOMAIN,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    if DOMAIN not in config:
        return True

    cfg = config[DOMAIN]
    entry_data = {
        CONF_USERNAME: cfg.get(CONF_USERNAME),
        CONF_PASSWORD: cfg.get(CONF_PASSWORD),
        CONF_SCHOOL: cfg.get(CONF_SCHOOL),
        CONF_STUDENT_ID: cfg.get(CONF_STUDENT_ID),
        CONF_UPDATE_INTERVAL: cfg.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        CONF_WEEKS_AHEAD: cfg.get(CONF_WEEKS_AHEAD, DEFAULT_WEEKS_AHEAD),
    }

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=entry_data,
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    client = MagisterApiClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        school=entry.data[CONF_SCHOOL],
        student_id=str(entry.data[CONF_STUDENT_ID]),
        weeks_ahead=int(entry.data.get(CONF_WEEKS_AHEAD, DEFAULT_WEEKS_AHEAD)),
    )

    coordinator = HaSchoolCoordinator(
        hass,
        client,
        update_interval=int(entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
