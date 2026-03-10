from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class MagisterLesson:
    id: str
    subject: str
    start: str
    end: str
    location: str | None = None
    teacher: str | None = None
    note: str | None = None


@dataclass
class MagisterHomework:
    id: str
    title: str
    due: str
    description: str | None = None
    subject: str | None = None


class MagisterApiClient:
    """Placeholder client; vervang met echte auth/endpoints uit Charles-captures."""

    def __init__(self, username: str, password: str, school: str, student_id: str) -> None:
        self._username = username
        self._password = password
        self._school = school
        self._student_id = student_id
        self._token: str | None = None

    async def authenticate(self) -> None:
        await asyncio.sleep(0)
        # TODO: implementeer auth-flow
        self._token = "todo"

    async def async_get_schedule(self) -> list[MagisterLesson]:
        await asyncio.sleep(0)
        # TODO: implementeer endpoint parsing
        return []

    async def async_get_homework(self) -> list[MagisterHomework]:
        await asyncio.sleep(0)
        # TODO: implementeer endpoint parsing
        return []

    async def async_fetch_all(self) -> dict[str, Any]:
        if not self._token:
            await self.authenticate()
        lessons = await self.async_get_schedule()
        homework = await self.async_get_homework()
        return {"schedule": lessons, "homework": homework}
