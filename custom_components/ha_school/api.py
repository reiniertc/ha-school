from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import aiohttp


_TAG_RE = re.compile(r"<[^>]+>")

# Bekende tenant mapping uit captures; uitbreidbaar.
KNOWN_TENANTS: dict[str, str] = {
    "nuovo": "b8b13071f92b44d08936eb9c92d519ab",
}


def _strip_html(value: str | None) -> str | None:
    if not value:
        return None
    text = _TAG_RE.sub(" ", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _pkce_pair() -> tuple[str, str]:
    verifier = _b64url(os.urandom(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


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
    completed: bool = False


@dataclass
class MagisterHomework:
    id: str
    title: str
    due: str
    description: str | None = None
    subject: str | None = None
    teacher: str | None = None
    has_attachments: bool = False
    completed: bool = False


class MagisterApiClient:
    def __init__(self, username: str, password: str, school: str, student_id: str, weeks_ahead: int) -> None:
        self._username = username
        self._password = password
        self._school = school
        self._student_id = student_id
        self._weeks_ahead = max(1, weeks_ahead)

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: datetime | None = None

    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def _tenant_id(self) -> str:
        return KNOWN_TENANTS.get(self._school.lower(), "")

    async def _request_token_with_refresh(self) -> None:
        if not self._refresh_token:
            raise RuntimeError("Geen refresh token beschikbaar")

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            form = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": "magister-lo-app",
            }
            async with session.post(
                "https://accounts.magister.net/connect/token",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Refresh token mislukt ({resp.status})")
                payload = await resp.json()

        self._access_token = payload.get("access_token")
        self._refresh_token = payload.get("refresh_token", self._refresh_token)
        expires_in = int(payload.get("expires_in", 3600))
        self._expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 60)

    async def authenticate(self) -> None:
        tenant_id = self._tenant_id
        if not tenant_id:
            raise RuntimeError(
                f"Geen tenant_id mapping voor school '{self._school}'. Voeg deze toe in KNOWN_TENANTS."
            )

        verifier, challenge = _pkce_pair()
        state = secrets.token_urlsafe(16)

        auth_params = {
            "response_type": "code",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "client_id": "magister-lo-app",
            "scope": "email offline_access openid profile magister.zen calendar.to-do.user attendance.overview attendance.administration calendar.user lockers.administration",
            "redirect_uri": "m6loapp://oauth2redirect/",
            "prompt": "login",
            "acr_values": f"tenant:{tenant_id}",
            "login_hint": self._username,
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
            # 1) Start authorize flow
            async with session.get("https://accounts.magister.net/connect/authorize", params=auth_params) as resp:
                final_url = str(resp.url)
                _ = await resp.text()

            parsed = urlparse(final_url)
            query = parse_qs(parsed.query)
            session_id = (query.get("sessionId") or [None])[0]
            return_url = (query.get("returnUrl") or [None])[0]
            if not session_id or not return_url:
                raise RuntimeError("Kon sessionId/returnUrl niet bepalen uit authorize flow")

            # 2) challenge current
            xsrf = session.cookie_jar.filter_cookies("https://accounts.magister.net").get("XSRF-TOKEN")
            xsrf_value = xsrf.value if xsrf else ""
            auth_code = secrets.token_hex(7)

            current_payload = {
                "sessionId": session_id,
                "returnUrl": return_url,
                "authCode": auth_code,
            }

            async with session.post(
                "https://accounts.magister.net/challenges/current",
                json=current_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "x-xsrf-token": xsrf_value,
                    "Origin": "https://accounts.magister.net",
                    "Referer": "https://accounts.magister.net/",
                },
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"challenges/current mislukt ({resp.status})")
                _ = await resp.json()

            # XSRF kan gewijzigd zijn
            xsrf = session.cookie_jar.filter_cookies("https://accounts.magister.net").get("XSRF-TOKEN")
            xsrf_value = xsrf.value if xsrf else ""

            # 3) password challenge
            pwd_payload = {
                "sessionId": session_id,
                "returnUrl": return_url,
                "authCode": auth_code,
                "password": self._password,
                "userWantsToPairSoftToken": False,
                "userSkippedFido": False,
                "m_ChT": 2720,
                "m_ChF": 0,
            }

            async with session.post(
                "https://accounts.magister.net/challenges/password",
                json=pwd_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "x-xsrf-token": xsrf_value,
                    "Origin": "https://accounts.magister.net",
                    "Referer": "https://accounts.magister.net/",
                },
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"challenges/password mislukt ({resp.status})")
                pwd_result = await resp.json()

            redirect_url = pwd_result.get("redirectURL")
            if not redirect_url:
                raise RuntimeError("Geen redirectURL na password challenge")

            # 4) callback, code ophalen zonder app-redirect te volgen
            async with session.get(
                f"https://accounts.magister.net{redirect_url}",
                allow_redirects=False,
            ) as resp:
                location = resp.headers.get("Location", "")

            if not location.startswith("m6loapp://oauth2redirect/"):
                raise RuntimeError("Geen app redirect ontvangen met authorization code")

            parsed_cb = urlparse(location)
            code = (parse_qs(parsed_cb.query).get("code") or [None])[0]
            if not code:
                raise RuntimeError("Authorization code ontbreekt in callback")

            # 5) token exchange
            form = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "m6loapp://oauth2redirect/",
                "code_verifier": verifier,
                "client_id": "magister-lo-app",
            }
            async with session.post(
                "https://accounts.magister.net/connect/token",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"connect/token mislukt ({resp.status})")
                token_payload = await resp.json()

        self._access_token = token_payload.get("access_token")
        self._refresh_token = token_payload.get("refresh_token")
        expires_in = int(token_payload.get("expires_in", 3600))
        self._expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 60)

    async def _ensure_token(self) -> None:
        if self._access_token and self._expires_at and datetime.now(UTC) < self._expires_at:
            return

        if self._refresh_token:
            try:
                await self._request_token_with_refresh()
                return
            except Exception:
                # fallback volledige login
                pass

        await self.authenticate()

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
            completed=bool(item.get("Afgerond")),
        )

    async def async_get_schedule(self) -> list[MagisterLesson]:
        await self._ensure_token()
        if not self._access_token:
            return []

        today = datetime.now(UTC).date()
        end_date = today + timedelta(weeks=self._weeks_ahead)

        url = f"https://{self._school}.magister.net/api/personen/{self._student_id}/afspraken"
        params = {
            "van": today.isoformat(),
            "tot": end_date.isoformat(),
        }
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "API-Version": "1.0",
            "X-API-Client-ID": "EF15",
            "Accept": "*/*",
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 401:
                    # token verlopen, 1x refresh + retry
                    await self._request_token_with_refresh()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    async with session.get(url, params=params, headers=headers) as retry:
                        if retry.status != 200:
                            text = await retry.text()
                            raise RuntimeError(f"Afspraken ophalen mislukt ({retry.status}): {text[:200]}")
                        payload = await retry.json()
                elif resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Afspraken ophalen mislukt ({resp.status}): {text[:200]}")
                else:
                    payload = await resp.json()

        items = payload.get("Items", [])
        return [self._lesson_from_item(item) for item in items]

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
                        completed=lesson.completed,
                    )
                )

        return homework

    async def async_fetch_all(self) -> dict[str, Any]:
        lessons = await self.async_get_schedule()
        homework = await self.async_get_homework(lessons)

        return {
            "schedule": lessons,
            "homework": homework,
            "source": "afspraken",
            "homework_rule": "Inhoud/Opmerking not empty",
            "weeks_ahead": self._weeks_ahead,
        }
