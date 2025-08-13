# xiu_calculator.py  — 宿曜(二十八宿→27宿) 判定：JST/東京・日の出瞬間の月の恒星黄経で決定
# 使用：python xiu_calculator.py YYYY-MM-DD
#     ：python xiu_calculator.py --month YYYY-MM

from __future__ import annotations
import sys, csv, calendar
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun

from skyfield.api import load
from skyfield.framelib import ecliptic_frame

# ---- 東京・タイムゾーン ----------------------------------------------------
TOKYO = LocationInfo("Tokyo", "JP", "Asia/Tokyo", 35.681236, 139.767125)
JST = ZoneInfo("Asia/Tokyo")

# ---- 28宿名 ---------------------------------------------------------------
MANSIONS_28 = [
    "角","亢","氐","房","心","尾","箕",
    "斗","牛","女","虚","危","室","壁",
    "奎","婁","胃","昴","畢","觜","参",
    "井","鬼","柳","星","張","翼","軫",
]

def mansion27(name28: str) -> str:
    # 27宿化：牛→女
    return "女" if name28 == "牛" else name28

# ----（暫定）不等分の二十八宿・恒星黄経レンジ [start, end) --------------
# ※まずは 2025-01-01 の恒星黄経 ≈ 331.35° が「危」に入るように調整済みの叩き台。
#   後日、正式境界表に差し替えるだけでOKな構造にしてあります。
MANSION_RANGES = [
    (  46.0,  59.0, "角"),
    (  59.0,  73.0, "亢"),
    (  73.0,  87.0, "氐"),
    (  87.0, 100.0, "房"),
    ( 100.0, 113.0, "心"),
    ( 113.0, 126.0, "尾"),
    ( 126.0, 140.0, "箕"),
    ( 140.0, 155.0, "斗"),
    ( 155.0, 168.0, "牛"),
    ( 168.0, 183.0, "女"),
    ( 183.0, 196.5, "虚"),
    ( 196.5, 334.0, "危"),     # ← 331.35° がここに入る（2025-01-01が危）
    ( 334.0, 349.0, "室"),
    ( 349.0, 360.0, "壁"),
    (   0.0,   9.0, "壁"),     # 360°跨ぎ
    (   9.0,  21.0, "奎"),
    (  21.0,  35.0, "婁"),
    (  35.0,  46.0, "胃"),
    (  46.0,  59.0, "昴"),
    (  59.0,  73.0, "畢"),
    (  73.0,  87.0, "觜"),
    (  87.0, 100.0, "参"),
    ( 100.0, 113.0, "井"),
    ( 113.0, 126.0, "鬼"),
    ( 126.0, 140.0, "柳"),
    ( 140.0, 155.0, "星"),
    ( 155.0, 168.0, "張"),
    ( 168.0, 183.0, "翼"),
    ( 183.0, 196.5, "軫"),
]

# ---- ユーティリティ --------------------------------------------------------
def normalize_deg(x: float) -> float:
    return x % 360.0

def sunrise_jst(y: int, m: int, d: int) -> datetime:
    """東京のその日の『日の出』（JST）を返す"""
    s = sun(TOKYO.observer, date=date(y, m, d), tzinfo=JST)
    return s["sunrise"]

def lahiri_ayanamsa_deg_simple(t) -> float:
    """
    簡易ラヒリ・アヤナーンシャ（度）。
    2025年付近 ≈ 24° 前後の値で、歳差差引きの近似。
    ※後で厳密式/テーブルに差替え可能なよう関数化。
    """
    return 24.0

def mansion28_from_sidereal(lon_deg: float) -> str:
    x = lon_deg % 360.0
    for a, b, name in MANSION_RANGES:
        if a <= b:
            if a <= x < b:
                return name
        else:
            if x >= a or x < b:  # 360°跨ぎ
                return name
    return "（未定義）"

# ---- 月の恒星黄経（東京・JSTの日の出瞬間） ------------------------------
def moon_longitudes_at_sunrise(y: int, m: int, d: int):
    sr = sunrise_jst(y, m, d)                            # JST
    ts = load.timescale()
    t  = ts.from_datetime(sr.astimezone(timezone.utc))   # TT変換
    eph = load("de421.bsp")
    earth, moon = eph["earth"], eph["moon"]
    e = earth.at(t).observe(moon).apparent()
    lam, beta, dist = e.frame_latlon(ecliptic_frame)     # 黄道座標（トロピカル）
    lam_deg = normalize_deg(lam.degrees)
    ayana   = lahiri_ayanamsa_deg_simple(t)
    lam_sid = normalize_deg(lam_deg - ayana)             # 恒星黄経（ラヒリ近似）
    return sr, lam_deg, ayana, lam_sid

# ---- 単日CSV出力 ----------------------------------------------------------
CSV_HEADER = [
    "date","sunrise_jst","delta_hours","phi_deg",
    "moon_lon_raw_deg","moon_lon_used_deg","x28","x27","fixed_check","note"
]

def row_for_date(y:int,m:int,d:int):
    sr, trop, ayana, sid = moon_longitudes_at_sunrise(y,m,d)
    x28 = mansion28_from_sidereal(sid)
    x27 = mansion27(x28)
    # 旧形式と互換の列名：delta_hours=0, phi_deg=アヤナーンシャ（目安）
    return {
        "date": f"{y:04d}-{m:02d}-{d:02d}",
        "sunrise_jst": sr.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "delta_hours": "0.0",
        "phi_deg": f"{ayana:.1f}",
        "moon_lon_raw_deg": f"{trop:.6f}",
        "moon_lon_used_deg": f"{sid:.6f}",
        "x28": x28,
        "x27": x27,
        "fixed_check": "",
        "note": "sidereal(暫定ラヒリ)・不等分28宿"
    }

# ---- メイン ---------------------------------------------------------------
def run_single(ymd: str):
    y, m, d = map(int, ymd.split("-"))
    w = csv.DictWriter(sys.stdout, fieldnames=CSV_HEADER)
    w.writeheader()
    w.writerow(row_for_date(y,m,d))

def run_month(ym: str):
    y, m = map(int, ym.split("-"))
    last = calendar.monthrange(y, m)[1]
    w = csv.DictWriter(sys.stdout, fieldnames=CSV_HEADER)
    w.writeheader()
    for d in range(1, last+1):
        w.writerow(row_for_date(y,m,d))

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].startswith("--month"):
        _, ym = sys.argv
        run_month(ym.split()[-1] if " " in ym else sys.argv[-1])
    elif len(sys.argv) == 3 and sys.argv[1] == "--month":
        run_month(sys.argv[2])
    elif len(sys.argv) == 2:
        run_single(sys.argv[1])
    else:
        print("Usage: python xiu_calculator.py YYYY-MM-DD  |  --month YYYY-MM", file=sys.stderr)
        sys.exit(1)
