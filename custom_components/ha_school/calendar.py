from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .api import MagisterLesson
from .const import DOMAIN
from .coordinator import HaSchoolCoordinator


def _to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return dt_util.parse_datetime(value)


def _event_title(lesson: MagisterLesson) -> str:
    prefix = ""

    if lesson.status == 5:
        prefix += "*VERVALLEN* "
            
    if lesson.info_type == 2:
        prefix = "*PROEFWERK* "

    if lesson.note:
        return f"{prefix}{lesson.subject}"

    return f"{prefix}{lesson.subject}"


def _lesson_to_event(lesson: MagisterLesson) -> CalendarEvent | None:
    start = _to_dt(lesson.start)
    end = _to_dt(lesson.end)
    if not start or not end:
        return None

    details: list[str] = []
    if lesson.note:
        prefix = "[afgerond] " if lesson.completed else ""
        details.append(f"{prefix}{lesson.note}")

    return CalendarEvent(
        summary=_event_title(lesson),
        start=start,
        end=end,
        description="\n".join(details) if details else None,
        location=lesson.location,
        uid=lesson.id,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HaSchoolCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HaSchoolCalendarEntity(coordinator)])


class HaSchoolCalendarEntity(CoordinatorEntity[HaSchoolCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Rooster"

    def __init__(self, coordinator: HaSchoolCoordinator) -> None:
        super().__init__(coordinator)
        sid = coordinator.client.student_id
        self._attr_object_id = f"ha_school_{sid}_rooster"
        self._attr_unique_id = f"ha_school_{sid}_calendar"

    def _get_next_lesson(self) -> MagisterLesson | None:
        if not self.coordinator.data:
            return None

        now = dt_util.utcnow()
        lessons: list[MagisterLesson] = self.coordinator.data.get("schedule", [])
        upcoming = sorted(lessons, key=lambda item: item.start)

        for lesson in upcoming:
            start = _to_dt(lesson.start)
            if start and start >= now:
                return lesson

        return None

    @property
    def event(self) -> CalendarEvent | None:
        lesson = self._get_next_lesson()
        if not lesson:
            return None
        return _lesson_to_event(lesson)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        lesson = self._get_next_lesson()
        if not lesson:
            return {}

        return {
            "info_type": lesson.info_type,
        }

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        if not self.coordinator.data:
            return []

        events: list[CalendarEvent] = []
        lessons: list[MagisterLesson] = self.coordinator.data.get("schedule", [])

        for lesson in lessons:
            start = _to_dt(lesson.start)
            if not start:
                continue
            if start_date <= start <= end_date:
                event = _lesson_to_event(lesson)
                if event:
                    events.append(event)

        return sorted(events, key=lambda item: item.start)
