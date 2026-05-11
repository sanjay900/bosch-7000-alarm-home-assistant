"""Types for the Bosch Alarm integration."""

from bosch_alarm_map.panel import Panel

from homeassistant.config_entries import ConfigEntry

type BoschAlarmConfigEntry = ConfigEntry[Panel]
