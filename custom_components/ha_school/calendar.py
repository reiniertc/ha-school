from __future__ import annotations

from datetime import datetime

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
    # [*] = er is huiswerk/info en afspraak staat niet afgerond
    if lesson.note and not lesson.completed:
        return f"[*] {lesson.subject}"
    return lesson.subject


def _lesson_to_event(lesson: MagisterLesson) -> CalendarEvent | None:
    start = _to_dt(lesson.start)
    end = _to_dt(lesson.end)
    if not start or not end:
        return None

    details: list[str] = []
    if lesson.teacher:
        details.append(f"Docent: {lesson.teacher}")
    if lesson.location:
        details.append(f"Locatie: {lesson.location}")
    if lesson.note:
        details.append("")
        details.append("Huiswerk / inhoud:")
        details.append(lesson.note)
    if lesson.has_attachments:
        details.append("")
        details.append("Heeft bijlagen: ja")

    return CalendarEvent(
        summary=_event_title(lesson),
        start=start,
        end=end,
        description="\n".join(details) if details else None,
        location=lesson.location,
        uid=lesson.id,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: HaSchoolCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HaSchoolCalendarEntity(coordinator)])


class HaSchoolCalendarEntity(CoordinatorEntity[HaSchoolCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Rooster"
    _attr_unique_id = "ha_school_calendar"

    def __init__(self, coordinator: HaSchoolCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def event(self) -> CalendarEvent | None:
        if not self.coordinator.data:
            return None

        now = dt_util.utcnow()
        lessons: list[MagisterLesson] = self.coordinator.data.get("schedule", [])
        upcoming = sorted(lessons, key=lambda item: item.start)

        for lesson in upcoming:
            start = _to_dt(lesson.start)
            if start and start >= now:
                return _lesson_to_event(lesson)
        return None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
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
