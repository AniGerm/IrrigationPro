"""ETo (Evapotranspiration) calculation using FAO Penman-Monteith method."""
from __future__ import annotations

import math
from datetime import datetime


def calculate_eto(
    min_temp: float,
    max_temp: float,
    humidity: float,
    pressure: float,
    wind_speed: float,
    solar_radiation: float,
    altitude: float,
    latitude: float,
    date: datetime,
) -> float:
    """
    Calculate reference evapotranspiration (ETo) using FAO-56 Penman-Monteith.

    Args:
        min_temp: Minimum temperature (°C)
        max_temp: Maximum temperature (°C)
        humidity: Relative humidity (%)
        pressure: Atmospheric pressure (hPa)
        wind_speed: Wind speed (m/s)
        solar_radiation: Solar radiation (kWh/m²/day)
        altitude: Altitude (m)
        latitude: Latitude (decimal degrees)
        date: Date for calculation

    Returns:
        ETo in mm/day
    """
    # Mean temperature
    t_mean = (max_temp + min_temp) / 2
    
    # Convert solar radiation from kWh/day to MJ/m²/day
    r_s = solar_radiation * 3.6
    
    # Wind speed at 2m height (assuming measurement at 10m, apply conversion factor)
    u_2 = wind_speed * 0.748
    
    # Slope of saturation vapor pressure curve (kPa/°C)
    slope_svpc = (
        4098 * (0.6108 * math.exp((17.27 * t_mean) / (t_mean + 237.3)))
        / math.pow((t_mean + 237.3), 2)
    )
    
    # Atmospheric pressure (convert hPa to kPa)
    p_a = pressure / 10
    
    # Psychrometric constant (kPa/°C)
    psc = p_a * 0.000665
    
    # Delta term for radiation
    dt = slope_svpc / (slope_svpc + (psc * (1 + (0.34 * u_2))))
    
    # Psi term for wind
    pt = psc / (slope_svpc + (psc * (1 + (0.34 * u_2))))
    
    # Temperature term for wind
    tt = u_2 * (900 / (t_mean + 273))
    
    # Saturation vapor pressure (kPa)
    e_t_max = 0.6108 * math.exp(17.27 * max_temp / (max_temp + 237.3))
    e_t_min = 0.6108 * math.exp(17.27 * min_temp / (min_temp + 237.3))
    e_s = (e_t_max + e_t_min) / 2
    
    # Actual vapor pressure (kPa)
    e_a = humidity * e_s / 100
    
    # Julian day
    start_of_year = datetime(date.year, 1, 1, tzinfo=date.tzinfo)
    doy = (date - start_of_year).days + 1
    
    # Inverse relative distance Earth-Sun
    d_r = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    
    # Solar declination (rad)
    s_d = 0.409 * math.sin((2 * math.pi * doy / 365) - 1.39)
    
    # Latitude in radians
    l_rad = latitude * math.pi / 180
    
    # Sunset hour angle (rad)
    sunset_ha = math.acos(-(math.tan(s_d) * math.tan(l_rad)))
    
    # Extraterrestrial radiation (MJ/m²/day)
    r_a = (
        (1440 / math.pi)
        * 0.082
        * d_r
        * (
            (sunset_ha * math.sin(l_rad) * math.sin(s_d))
            + (math.cos(l_rad) * math.cos(s_d) * math.sin(sunset_ha))
        )
    )
    
    # Clear sky radiation (MJ/m²/day)
    r_so = r_a * (0.75 + (2 * altitude / 100000))
    
    # Net shortwave radiation (MJ/m²/day) - albedo of 0.23
    r_ns = r_s * (1 - 0.23)
    
    # Net longwave radiation (MJ/m²/day)
    r_nl = (
        4.903
        * math.pow(10, -9)
        * (math.pow((273.16 + max_temp), 4) + math.pow((273.16 + min_temp), 4))
        / 2
    )
    r_nl = r_nl * (0.34 - (0.14 * math.sqrt(e_a)))
    r_nl = r_nl * ((1.35 * r_s / r_so) - 0.35)
    
    # Net radiation (MJ/m²/day)
    r_n = r_ns - r_nl
    
    # Soil heat flux (assumed negligible for daily calculation)
    r_ng = 0.408 * r_n
    
    # Radiation term
    et_rad = dt * r_ng
    
    # Wind term
    et_wind = pt * tt * (e_s - e_a)
    
    # Reference evapotranspiration (mm/day)
    eto = et_rad + et_wind
    
    return max(0, eto)  # Ensure non-negative
