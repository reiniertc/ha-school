from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_PASSWORD,
    CONF_SCHOOL,
    CONF_STUDENT_ID,
    CONF_UPDATE_INTERVAL,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


class HaSchoolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="HA School", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_SCHOOL): str,
                vol.Required(CONF_STUDENT_ID): str,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, user_input=None):
        if user_input is None:
            return self.async_abort(reason="invalid_import")

        await self.async_set_unique_id(f"{user_input.get(CONF_SCHOOL)}-{user_input.get(CONF_STUDENT_ID)}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="HA School", data=user_input)
