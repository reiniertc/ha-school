from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    text = _TAG_RE.sub(" ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


@dataclass
class MagisterLesson:
    id: str
    subject: str
    start: str
    end: str
    location: str | None = None
    teacher: str | None = None
    note: str | None = None
    has_attachments: bool = False
    info_type: int = 0


@dataclass
class MagisterHomework:
    id: str
    title: str
    due: str
    description: str | None = None
    subject: str | None = None
    teacher: str | None = None
    has_attachments: bool = False


class MagisterApiClient:
    """Client scaffold.

    Auth-flow is nog TODO; parsing/logica voor huiswerk-via-afspraken staat wel klaar.
    """

    def __init__(self, username: str, password: str, school: str, student_id: str) -> None:
        self._username = username
        self._password = password
        self._school = school
        self._student_id = student_id
        self._token: str | None = None

    async def authenticate(self) -> None:
        await asyncio.sleep(0)
        # TODO: implementeer volledige Magister auth-flow uit Charles captures.
        self._token = "todo"

    @staticmethod
    def _lesson_from_item(item: dict[str, Any]) -> MagisterLesson:
        subject = (item.get("Vakken") or [{}])[0].get("Naam") or item.get("Omschrijving") or "Onbekend"
        teacher = (item.get("Docenten") or [{}])[0].get("Naam")
        location = item.get("Lokatie") or ((item.get("Lokalen") or [{}])[0].get("Naam"))

        return MagisterLesson(
            id=str(item.get("Id")),
            subject=subject,
            start=item.get("Start", ""),
            end=item.get("Einde", ""),
            location=location,
            teacher=teacher,
            note=_strip_html(item.get("Inhoud")) or _strip_html(item.get("Opmerking")),
            has_attachments=bool(item.get("HeeftBijlagen")),
            info_type=int(item.get("InfoType") or 0),
        )

    async def async_get_schedule(self) -> list[MagisterLesson]:
        await asyncio.sleep(0)
        # TODO: implementeer endpoint call /api/personen/{id}/afspraken
        return []

    async def async_get_homework(self, lessons: list[MagisterLesson] | None = None) -> list[MagisterHomework]:
        if lessons is None:
            lessons = await self.async_get_schedule()

        homework: list[MagisterHomework] = []
        for lesson in lessons:
            if lesson.note:
                homework.append(
                    MagisterHomework(
                        id=lesson.id,
                        title=lesson.subject,
                        due=lesson.start,
                        description=lesson.note,
                        subject=lesson.subject,
                        teacher=lesson.teacher,
                        has_attachments=lesson.has_attachments,
                    )
                )

        return homework

    async def async_fetch_all(self) -> dict[str, Any]:
        if not self._token:
            await self.authenticate()

        lessons = await self.async_get_schedule()
        homework = await self.async_get_homework(lessons)

        return {
            "schedule": lessons,
            "homework": homework,
            "source": "afspraken",
            "homework_rule": "Inhoud/Opmerking not empty",
        }
