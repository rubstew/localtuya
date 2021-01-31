"""Platform to locally control Tuya-based switch devices."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    ClimateEntity,
)

from homeassistant.components.climate.const import (  # HVAC_MODE_COOL,; HVAC_MODE_FAN_ONLY,; SUPPORT_TARGET_HUMIDITY,; SUPPORT_PRESET_MODE,; SUPPORT_SWING_MODE,; SUPPORT_AUX_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_FAN_MODE_DP,
    CONF_HVAC_MODE_DP,
    CONF_MAX_TEMP_DP,
    CONF_MIN_TEMP_DP,
    CONF_PRECISION,
    CONF_MODE,
    CONF_PRECISION_TARGET,
    CONF_ACTION,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_TEMPERATURE_STEP,
)

_LOGGER = logging.getLogger(__name__)

TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS
DEFAULT_PRECISION = PRECISION_TENTHS
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_MODE): vol.In(dps),
        vol.Optional(CONF_ACTION): vol.In(dps),
        vol.Optional(CONF_PRECISION_TARGET): vol.In(dps),
        vol.Optional(CONF_TEMPERATURE_STEP): vol.In(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_HVAC_MODE_DP): vol.In(dps),
        vol.Optional(CONF_FAN_MODE_DP): vol.In(dps),
        vol.Optional(CONF_MAX_TEMP_DP): vol.In(dps),
        vol.Optional(CONF_MIN_TEMP_DP): vol.In(dps),
        vol.Optional(CONF_PRECISION): vol.In(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_TEMPERATURE_UNIT): vol.In(
            [TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT]
        ),
    }


class LocaltuyaClimate(LocalTuyaEntity, ClimateEntity):
    """Representation of a Tuya switch."""

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize the Tuya switch."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._target_temperature = None
        self._current_temperature = None
        self._hvac_mode = None
        self._hvac_action = None
        self._preset_mode = None
        self._precision = self._config.get(CONF_PRECISION, DEFAULT_PRECISION)
        _LOGGER.debug("CLIMATE: Initiated")

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        return self._hvac_mode
    
    @property
    def hvac_action(self):
        return self._hvac_action

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return {HVAC_MODE_OFF, HVAC_MODE_AUTO, HVAC_MODE_HEAT}
    
    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            supported_features = supported_features | SUPPORT_TARGET_TEMPERATURE
        if self.has_config(CONF_MAX_TEMP_DP):
            supported_features = supported_features | SUPPORT_TARGET_TEMPERATURE_RANGE
        if self.has_config(CONF_FAN_MODE_DP):
            supported_features = supported_features | SUPPORT_FAN_MODE
        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        if (
            self._config.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
            == TEMPERATURE_FAHRENHEIT
        ):
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._config.get(CONF_TEMPERATURE_STEP, DEFAULT_TEMPERATURE_STEP)

    async def async_turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        await self._device.set_dp(True, self._dp_id)

    async def async_turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        await self._device.set_dp(False, self._dp_id)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self.has_config(CONF_TARGET_TEMPERATURE_DP):
            temperature = round(kwargs[ATTR_TEMPERATURE] )
            await self._device.set_dp(temperature, self._config[CONF_TARGET_TEMPERATURE_DP])
    
    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        if hvac_mode == HVAC_MODE_OFF:
            if self._state == False:
                await self._device.set_dp(True, self._dp_id)
            else:
                await self._device.set_dp(False, self._dp_id)
        if hvac_mode != HVAC_MODE_OFF and self._state == False:
            await self._device.set_dp(True, self._dp_id)
        if hvac_mode == HVAC_MODE_HEAT:
            await self._device.set_dp("manual", self._config[CONF_HVAC_MODE_DP])
        if hvac_mode == HVAC_MODE_AUTO:
            await self._device.set_dp("auto", self._config[CONF_HVAC_MODE_DP])
            



    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            self._target_temperature = (
                self.dps_conf(CONF_TARGET_TEMPERATURE_DP)
            )

        if self.has_config(CONF_CURRENT_TEMPERATURE_DP):
            self._current_temperature = (
                self.dps_conf(CONF_CURRENT_TEMPERATURE_DP) * self._precision
            )
        hvac_mode = HVAC_MODE_OFF
        if self.has_config(CONF_HVAC_MODE_DP):
            hvac_mode = self.dps_conf(CONF_HVAC_MODE_DP)
        
        if self._state is False:
            self._hvac_mode = HVAC_MODE_OFF
            
        elif hvac_mode == HVAC_MODE_AUTO:
            self._hvac_mode = HVAC_MODE_AUTO
        else:
            self._hvac_mode = HVAC_MODE_HEAT
        
        if self.has_config(CONF_ACTION):
            if self.dps_conf(CONF_ACTION) == "open":
                self._hvac_action = CURRENT_HVAC_HEAT
            elif self._state is False:
                self._hvac_action = CURRENT_HVAC_OFF
            else:
                self._hvac_action = CURRENT_HVAC_IDLE


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaClimate, flow_schema)
