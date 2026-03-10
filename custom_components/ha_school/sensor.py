from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .coordinator import HaSchoolCoordinator
from .const import DOMAIN


def _format_dt(value: str) -> str:
    dt_value = dt_util.parse_datetime(value)
    if not dt_value:
        return value
    local = dt_util.as_local(dt_value)
    return local.strftime("%Y-%m-%d %H:%M")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HaSchoolCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HaSchoolLessonsCountSensor(coordinator),
            HaSchoolHomeworkCountSensor(coordinator),
            HaSchoolHomeworkOverviewSensor(coordinator),
        ]
    )


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
                "afgerond": item.completed,
                "tekst": item.description,
            }
            for item in homework[:5]
        ]

        return {
            "bron": self.coordinator.data.get("source", "afspraken"),
            "regel": self.coordinator.data.get("homework_rule", "Inhoud/Opmerking not empty"),
            "preview": preview,
        }


class HaSchoolHomeworkOverviewSensor(_BaseHaSchoolSensor):
    _attr_name = "Huiswerk overzicht"
    _attr_unique_id = "ha_school_homework_overview"
    _attr_icon = "mdi:format-list-bulleted"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return 0
        items = self.coordinator.data.get("homework", [])
        # alleen open huiswerk
        return len([item for item in items if not item.completed])

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return None

        items = self.coordinator.data.get("homework", [])
        open_items = [item for item in items if not item.completed]

        lines = []
        structured = []
        for item in sorted(open_items, key=lambda hw: hw.due):
            moment = _format_dt(item.due)
            title = item.subject or item.title or "Onbekend vak"
            text = item.description or ""
            line = f"- {moment} | {title}: {text}".strip()
            lines.append(line)
            structured.append(
                {
                    "id": item.id,
                    "vak": title,
                    "moment": item.due,
                    "moment_local": moment,
                    "tekst": text,
                    "docent": item.teacher,
                    "heeft_bijlagen": item.has_attachments,
                }
            )

        return {
            "periode_weken": self.coordinator.data.get("weeks_ahead", 4),
            "open_huiswerk": structured,
            "tekst": "\n".join(lines),
            "gegenereerd_op": datetime.now().isoformat(),
        }
