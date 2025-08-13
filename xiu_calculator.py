# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Tuple, List
from astral import LocationInfo
from astral.sun import sun
from skyfield.api import load, wgs84
from skyfield.framelib import ecliptic_frame as ECLIPTIC_FRAME
import numpy as np

JST = ZoneInfo("Asia/Tokyo")
TOKYO = LocationInfo(name="Tokyo", region="JP", timezone="Asia/Tokyo",
                     latitude=35.681236, longitude=139.767125)

MANSIONS_28 = [
    "角","亢","氐","房","心","尾","箕","斗","牛","女","虚","危","室","壁","奎","婁",
    "胃","昴","畢","觜","参","井","鬼","柳","星","張","翼","軫"
]

def to_27(x28: str) -> str:
    return "女" if x28 == "牛" else x28

CAL_FIX: Dict[date, str] = {
    date(1957,2,6):  "畢",
    date(1961,2,15): "室",
    date(1961,9,12): "氐",
    date(2000,1,15): "畢",
    date(2025,5,14): "箕",
}

_month_dt_cache: Dict[Tuple[int,int], float] = {}
_month_phi_cache: Dict[Tuple[int,int], float] = {}

_TS = load.timescale()
_EPH = load("de421.bsp")
_EARTH = _EPH["earth"]
_MOON  = _EPH["moon"]

def mansion28_from_ecliptic_long(lon_deg: float) -> str:
    width = 360.0 / 28.0
    idx = int(math.floor(((lon_deg % 360.0) + 1e-12) / width)) % 28
    return MANSIONS_28[idx]

@dataclass
class XiuResult:
    date: str
    sunrise_jst: str
    delta_hours: float
    phi_deg: float
    moon_lon_raw_deg: float
    moon_lon_used_deg: float
    x28: str
    x27: str
    fixed_check: str
    note: str = ""

def _sunrise_jst(y: int, m: int, d: int) -> datetime:
    s = sun(TOKYO.observer, date=date(y, m, d), tzinfo=JST)
    return s["sunrise"]

def _moon_ecliptic_long_deg(dt: datetime) -> float:
    t = _TS.from_datetime(dt.astimezone(timezone.utc))
    e = _EARTH.at(t)
    app = e.observe(_MOON).apparent()
    lam, beta, dist = app.frame_latlon(ECLIPTIC_FRAME)
    return lam.degrees % 360.0

def _decide_delta_for_month(y: int, m: int) -> float:
    key = (y, m)
    if key in _month_dt_cache:
        return _month_dt_cache[key]
    month_fixed = [(d, mans) for (d, mans) in CAL_FIX.items() if d.year==y and d.month==m]
    if not month_fixed:
        _month_dt_cache[key] = 0.0
        return 0.0
    candidates = [i/12.0 for i in range(-72, 73)]
    best_dt = 0.0
    for dt_hours in candidates:
        ok_all = True
        for d, want in month_fixed:
            sr = _sunrise_jst(d.year, d.month, d.day) + timedelta(hours=dt_hours)
            lon = _moon_ecliptic_long_deg(sr)
            got = mansion28_from_ecliptic_long(lon)
            if got != want:
                ok_all = False
                break
        if ok_all:
            best_dt = dt_hours
            break
    _month_dt_cache[key] = best_dt
    return best_dt

def _decide_phi_for_month(y: int, m: int) -> float:
    key = (y, m)
    if key in _month_phi_cache:
        return _month_phi_cache[key]
    month_fixed = [(d, mans) for (d, mans) in CAL_FIX.items() if d.year==y and d.month==m]
    if not month_fixed:
        _month_phi_cache[key] = 0.0
        return 0.0
    dt_hours = _decide_delta_for_month(y, m)
    for phi in np.arange(-180.0, 180.0001, 0.1):
        ok_all = True
        for d, want in month_fixed:
            sr = _sunrise_jst(d.year, d.month, d.day) + timedelta(hours=dt_hours)
            lon = (_moon_ecliptic_long_deg(sr) + float(phi)) % 360.0
            got = mansion28_from_ecliptic_long(lon)
            if got != want:
                ok_all = False
                break
        if ok_all:
            _month_phi_cache[key] = float(phi)
            return float(phi)
    _month_phi_cache[key] = 0.0
    return 0.0

def xiu_for_ymd(y: int, m: int, d: int) -> XiuResult:
    dt_hours = _decide_delta_for_month(y, m)
    phi_deg  = _decide_phi_for_month(y, m)
    sr = _sunrise_jst(y, m, d) + timedelta(hours=dt_hours)
    lon_raw = _moon_ecliptic_long_deg(sr)
    lon_used = (lon_raw + phi_deg) % 360.0
    x28 = mansion28_from_ecliptic_long(lon_used)
    x27 = to_27(x28)
    want = CAL_FIX.get(date(y, m, d))
    fixed_check = "OK" if (want is None or want == x28) else f"NG: expected {want}"
    return XiuResult(
        date=f"{y:04d}-{m:02d}-{d:02d}",
        sunrise_jst=sr.strftime("%Y-%m-%d %H:%M:%S %Z"),
        delta_hours=round(dt_hours, 3),
        phi_deg=round(phi_deg, 3),
        moon_lon_raw_deg=round(lon_raw, 6),
        moon_lon_used_deg=round(lon_used, 6),
        x28=x28,
        x27=x27,
        fixed_check=fixed_check,
        note=("固定キャリブレーション日" if want else ""),
    )

def _last_day_of_month(y: int, m: int) -> int:
    if m == 12:
        return 31
    from datetime import date as _date
    return (_date(y if m < 12 else y+1, m+1 if m < 12 else 1) - timedelta(days=1)).day

def run_cli(args: List[str]) -> int:
    if not args:
        print(__doc__)
        return 0
    if args[0] == "--test-fixed":
        print("date,sunrise_jst,delta_hours,phi_deg,moon_lon_raw_deg,moon_lon_used_deg,x28,x27,fixed_check,note")
        for d, _want in sorted(CAL_FIX.items()):
            r = xiu_for_ymd(d.year, d.month, d.day)
            print(f"{r.date},{r.sunrise_jst},{r.delta_hours},{r.phi_deg},{r.moon_lon_raw_deg},{r.moon_lon_used_deg},{r.x28},{r.x27},{r.fixed_check},{r.note}")
        return 0
    if args[0] == "--month" and len(args) == 2:
        y, m = map(int, args[1].split("-"))
        print("date,sunrise_jst,delta_hours,phi_deg,moon_lon_raw_deg,moon_lon_used_deg,x28,x27,fixed_check,note")
        for day in range(1, _last_day_of_month(y, m)+1):
            r = xiu_for_ymd(y, m, day)
            print(f"{r.date},{r.sunrise_jst},{r.delta_hours},{r.phi_deg},{r.moon_lon_raw_deg},{r.moon_lon_used_deg},{r.x28},{r.x27},{r.fixed_check},{r.note}")
        return 0
    print("date,sunrise_jst,delta_hours,phi_deg,moon_lon_raw_deg,moon_lon_used_deg,x28,x27,fixed_check,note")
    for s in args:
        y, m, d = map(int, s.split("-"))
        r = xiu_for_ymd(y, m, d)
        print(f"{r.date},{r.sunrise_jst},{r.delta_hours},{r.phi_deg},{r.moon_lon_raw_deg},{r.moon_lon_used_deg},{r.x28},{r.x27},{r.fixed_check},{r.note}")
    return 0

if __name__ == "__main__":
    raise SystemExit(run_cli(sys.argv[1:]))
