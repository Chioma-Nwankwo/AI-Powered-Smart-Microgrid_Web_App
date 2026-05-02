"""
Battery optimization endpoint — GET /api/optimize
Implements Linear Programming (MILP) battery dispatch per Chapter 3.8.4.
Objective: minimise total grid import cost over a 24-hour horizon.
Solver: CBC (bundled with PuLP, no extra install needed).
"""
from flask import Blueprint, request, jsonify
import numpy as np
import math
from pathlib import Path
from datetime import datetime, timedelta
import logging

try:
    import pulp
    _HAS_PULP = True
except ImportError:
    _HAS_PULP = False

from model_loader import model_loader

optimize_bp = Blueprint('optimize', __name__)
logger = logging.getLogger(__name__)

# Country geo info for timezone and daylight calculation
_GEO = {
    'nigeria':   {'lat':  9.0,  'utc':  1},
    'australia': {'lat': -25.0, 'utc': 10},
    'germany':   {'lat':  51.5, 'utc':  1},
    'canada':    {'lat':  56.0, 'utc': -5},
}

def _is_daytime(country: str, utc_dt) -> bool:
    geo = _GEO.get(country, {'lat': 0.0, 'utc': 0})
    local_hour = (utc_dt.hour + geo['utc']) % 24
    lat_rad = math.radians(geo['lat'])
    doy     = utc_dt.timetuple().tm_yday
    decl    = math.radians(23.45 * math.sin(math.radians(360 / 365 * (doy - 81))))
    cos_ha  = max(-1.0, min(1.0, -math.tan(lat_rad) * math.tan(decl)))
    ha_deg  = math.degrees(math.acos(cos_ha))
    return (12.0 - ha_deg / 15.0) <= local_hour < (12.0 + ha_deg / 15.0)


def _lp_dispatch(solar, load, capacity, max_rate, efficiency, prices):
    """
    MILP battery dispatch using PuLP / CBC.
    Variables: charge[h], discharge[h], soc[h], grid_import[h], b[h] (binary).
    Objective: minimise sum(grid_import[h] * prices[h]).
    Returns lists: charge, discharge, soc (fraction 0-1), grid_import.
    Falls back to greedy if PuLP is unavailable or solver fails.
    """
    H = len(solar)
    soc_init  = capacity * 0.5
    soc_min   = capacity * 0.10
    soc_max   = capacity * 0.95

    if not _HAS_PULP:
        return _greedy_dispatch(solar, load, capacity, max_rate, efficiency, prices, soc_init)

    prob = pulp.LpProblem("microgrid_dispatch", pulp.LpMinimize)

    # Decision variables
    charge      = [pulp.LpVariable(f"c_{h}", 0, max_rate)    for h in range(H)]
    discharge   = [pulp.LpVariable(f"d_{h}", 0, max_rate)    for h in range(H)]
    soc         = [pulp.LpVariable(f"soc_{h}", soc_min, soc_max) for h in range(H)]
    grid_import = [pulp.LpVariable(f"g_{h}", 0)              for h in range(H)]
    b           = [pulp.LpVariable(f"b_{h}", cat='Binary')   for h in range(H)]

    # Objective: minimise grid electricity cost
    prob += pulp.lpSum(grid_import[h] * prices[h] for h in range(H))

    for h in range(H):
        prev_soc = soc_init if h == 0 else soc[h - 1]

        # Battery state-of-charge dynamics
        prob += soc[h] == prev_soc + charge[h] * efficiency - discharge[h] / efficiency

        # Grid import must cover any shortfall: load + charge - solar - discharge
        prob += grid_import[h] >= load[h] + charge[h] - solar[h] - discharge[h]

        # Cannot charge and discharge simultaneously (MILP constraint)
        prob += charge[h]    <= max_rate * b[h]
        prob += discharge[h] <= max_rate * (1.0 - b[h])

    try:
        status = prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=10))
    except Exception as e:
        logger.warning("LP solver raised an exception (%s); using greedy fallback", e)
        return _greedy_dispatch(solar, load, capacity, max_rate, efficiency, prices, soc_init)

    if pulp.LpStatus[status] not in ('Optimal', 'Feasible'):
        logger.warning("LP solver did not find optimal solution (status %s); using greedy fallback", status)
        return _greedy_dispatch(solar, load, capacity, max_rate, efficiency, prices, soc_init)

    ch  = [max(0.0, pulp.value(charge[h])      or 0.0) for h in range(H)]
    dis = [max(0.0, pulp.value(discharge[h])   or 0.0) for h in range(H)]
    sc  = [max(soc_min, min(soc_max, pulp.value(soc[h]) or soc_init)) for h in range(H)]
    gi  = [max(0.0, pulp.value(grid_import[h]) or 0.0) for h in range(H)]
    return ch, dis, sc, gi


def _greedy_dispatch(solar, load, capacity, max_rate, efficiency, prices, soc_init):
    """Fallback greedy heuristic when PuLP is unavailable."""
    H   = len(solar)
    soc = soc_init
    ch, dis, sc, gi = [], [], [], []
    for h in range(H):
        surplus   = solar[h] - load[h]
        c = d = 0.0
        if surplus > 0 and soc < capacity * 0.95:
            c = min(surplus, max_rate, (capacity * 0.95 - soc) / efficiency)
            soc = min(soc + c * efficiency, capacity)
        elif surplus < 0 and soc > capacity * 0.10:
            d = min(-surplus, max_rate, (soc - capacity * 0.10) * efficiency)
            soc = max(soc - d / efficiency, 0)
        g = max(0.0, load[h] + c - solar[h] - d)
        ch.append(c); dis.append(d); sc.append(soc); gi.append(g)
    return ch, dis, sc, gi


@optimize_bp.route('', methods=['GET'], strict_slashes=False)
def get_optimization():
    """GET /api/optimize?country=nigeria&battery_capacity_kwh=100&panel_kw=50
    Returns 24-hour LP-optimised battery schedule.
    """
    try:
        return _run_optimization()
    except Exception as e:
        logger.error("Optimization route error: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


def _run_optimization():
    country  = request.args.get('country', 'nigeria').lower()
    capacity = float(request.args.get('battery_capacity_kwh', 100))
    panel_kw = float(request.args.get('panel_kw', 50))
    max_rate = capacity * 0.25     # C/4 charge/discharge rate limit
    efficiency = 0.95
    grid_cost_base = 0.15          # $/kWh baseline

    geo        = _GEO.get(country, {'lat': 0.0, 'utc': 0})
    utc_offset = geo['utc']

    # Get solar forecast for next 24 hours from trained ML model
    solar_result = model_loader.predict_next_hours(country, hours=24, target='solar_radiation_wm2')

    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    timestamps_24h = [now + timedelta(hours=h) for h in range(24)]

    raw_solar = solar_result['predictions'] if solar_result else [0.0] * 24
    # Convert W/m² → kW using panel capacity; zero at night (astronomical mask)
    solar = [
        max(0.0, float(v)) * (panel_kw / 1000.0) if _is_daytime(country, ts) else 0.0
        for v, ts in zip(raw_solar, timestamps_24h)
    ]

    # Synthetic load using LOCAL hour so peak aligns with country daytime
    local_hours = [(ts.hour + utc_offset) % 24 for ts in timestamps_24h]
    load = [max(10.0, 40 + 20 * np.sin((h - 6) * np.pi / 12) + np.random.normal(0, 2))
            for h in local_hours]

    # Time-of-use pricing per local hour
    prices = []
    for h_local in local_hours:
        if 18 <= h_local <= 21:
            prices.append(grid_cost_base * 1.5)   # peak tariff
        elif h_local < 7 or h_local > 22:
            prices.append(grid_cost_base * 0.8)   # off-peak tariff
        else:
            prices.append(grid_cost_base)

    # Run LP optimisation
    ch, dis, sc, gi = _lp_dispatch(solar, load, capacity, max_rate, efficiency, prices)

    # Build schedule and compute KPIs
    schedule             = []
    cost_with_battery    = 0.0
    cost_without_battery = 0.0

    for i, (h_local, sol, ld, c, d, s, g, p) in enumerate(
            zip(local_hours, solar, load, ch, dis, sc, gi, prices)):

        cost_with_battery    += g * p
        cost_without_battery += ld * p

        schedule.append({
            'hour':               h_local,
            'timestamp':          (now + timedelta(hours=i)).isoformat() + 'Z',
            'solar_generation':   round(sol, 2),
            'load':               round(ld,  2),
            'battery_charge':     round(c,   2),
            'battery_discharge':  round(d,   2),
            'state_of_charge':    round((s / capacity) * 100, 1),
            'grid_import':        round(g,   2),
            'price_per_kwh':      round(p,   3),
        })

    savings_pct   = max(0.0, (cost_without_battery - cost_with_battery)
                        / max(cost_without_battery, 1e-9) * 100)
    solar_total   = sum(solar)
    load_total    = sum(load)
    renewable_pct = min(100.0, solar_total / max(load_total, 1e-9) * 100)

    return jsonify({
        'country':   country,
        'capacity':  capacity,
        'solver':    'pulp_milp' if _HAS_PULP else 'greedy_fallback',
        'schedule':  schedule,
        'summary': {
            'cost_savings_pct':          round(savings_pct, 1),
            'renewable_utilization_pct': round(renewable_pct, 1),
            'total_solar_kwh':           round(solar_total, 2),
            'total_load_kwh':            round(load_total, 2),
            'cost_with_battery':         round(cost_with_battery, 2),
            'cost_without_battery':      round(cost_without_battery, 2),
        },
    })
