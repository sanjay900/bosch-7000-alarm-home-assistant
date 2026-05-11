"""The Bosch Alarm integration."""

from __future__ import annotations

from ssl import SSLError

from bosch_alarm_map.panel import Panel

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import ssl as ssl_util

from .const import CONF_INSTALLER_CODE, CONF_USER_CODE, DOMAIN
from .services import async_setup_services
from .types import BoschAlarmConfigEntry

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up bosch alarm services."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BoschAlarmConfigEntry) -> bool:
    """Set up Bosch Alarm from a config entry."""

    panel = Panel(
        session=async_get_clientsession(
            hass, verify_ssl=False, ssl_cipher=ssl_util.SSLCipherList.INTERMEDIATE
        ),
        host=entry.data[CONF_HOST],
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
    )
    try:
        await panel.load()
        entry.async_create_background_task(
            hass, panel.subscribe_to_events(), "bosch_alarm_subscribe"
        )
    except (PermissionError, ValueError) as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="authentication_failed"
        ) from err
    except (TimeoutError, OSError, ConnectionRefusedError, SSLError) as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
        ) from err

    entry.runtime_data = panel

    device_registry = dr.async_get(hass)

    desc = await panel.describe()

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        name=desc.friendly_name,
        manufacturer="Bosch Security Systems",
        model=desc.model_name,
        sw_version=desc.firmware_version,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BoschAlarmConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        pass
    return unload_ok
