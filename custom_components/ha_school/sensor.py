from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import HaSchoolCoordinator
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HaSchoolCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        HaSchoolLessonsCountSensor(coordinator),
        HaSchoolHomeworkCountSensor(coordinator),
    ])


class _BaseHaSchoolSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HaSchoolCoordinator) -> None:
        super().__init__(coordinator)


class HaSchoolLessonsCountSensor(_BaseHaSchoolSensor):
    _attr_name = "Rooster items"
    _attr_unique_id = "ha_school_lessons_count"
    _attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("schedule", [])) if self.coordinator.data else 0


class HaSchoolHomeworkCountSensor(_BaseHaSchoolSensor):
    _attr_name = "Huiswerk items"
    _attr_unique_id = "ha_school_homework_count"
    _attr_icon = "mdi:book-open-page-variant"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("homework", [])) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return None

        homework = self.coordinator.data.get("homework", [])
        preview = [
            {
                "vak": item.subject,
                "moment": item.due,
                "heeft_bijlagen": item.has_attachments,
                "tekst": item.description,
            }
            for item in homework[:5]
        ]

        return {
            "bron": self.coordinator.data.get("source", "afspraken"),
            "regel": self.coordinator.data.get("homework_rule", "Inhoud/Opmerking not empty"),
            "preview": preview,
        }
