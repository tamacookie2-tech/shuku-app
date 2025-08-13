import streamlit as st
from datetime import date, datetime
import subprocess, sys, json, os

st.set_page_config(page_title="宿曜（日の出基準・JST）", page_icon="✨", layout="centered")

st.title("宿曜 計算（JST・東京の日の出基準）")
st.caption("二十八宿→27宿（牛→女置換）、固定キャリブレーション日を満たす方式。")

# ── 単日計算 ───────────────────────────────────────────────
st.markdown("### 単日計算")
col1, col2 = st.columns([2,1])
with col1:
    day = st.date_input(
    "判定する日付",
    value=date(1961, 9, 12),
    min_value=date(1900, 1, 1),
    max_value=date(2050, 12, 31),
    key="single_date",
)

with col2:
    run_single = st.button("計算する", type="primary")

if run_single:
    ymd = day.strftime("%Y-%m-%d")
    cmd = [sys.executable, "xiu_calculator.py", ymd]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    # --- CSV出力から27宿だけを抽出 ---
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    mans27 = "取得失敗"
    if len(lines) >= 2:
        headers = [h.strip() for h in lines[0].split(",")]
        values  = [v.strip() for v in lines[1].split(",")]
        if "x27" in headers:
            mans27 = values[headers.index("x27")]

    # --- 画面には27宿だけを表示（大） ---
    st.markdown(f"## 本日の宿：**{mans27}**")

    # 必要な人だけ詳細（CSV全文）を確認
    with st.expander("計算の詳細（CSV）を表示"):
        st.code(proc.stdout or "(no output)", language="text")

# ── 月全体（CSV） ──────────────────────────────────────────
st.divider()
st.markdown("### 月全体（CSV）")
ym = st.text_input("年月（YYYY-MM）", value="1961-09")
run_month = st.button("CSVを生成")
if run_month:
    cmd = [sys.executable, "xiu_calculator.py", "--month", ym.strip()]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    csv_text = proc.stdout
    if csv_text:
        st.download_button("CSVをダウンロード", data=csv_text, file_name=f"{ym}.csv", mime="text/csv")
        st.code(csv_text.splitlines()[0] if csv_text else "(no output)")

st.divider()
st.caption("© 宿曜計算 — JST・東京の日の出基準／二十八宿→27宿（牛→女）。")
