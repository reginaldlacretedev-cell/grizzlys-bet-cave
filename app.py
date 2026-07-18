import streamlit as st
import datetime
import re
from pathlib import Path
from io import StringIO
import requests
from bs4 import BeautifulSoup
import pandas as pd
import shutil
import os

st.set_page_config(page_title="Grizzly's Bet Cave", layout="wide", initial_sidebar_state="expanded")

st.title("🐻 Grizzly's Bet Cave - MLB +1.5 Research")
st.caption("Daily Data-Driven +1.5 Run Line Picks")

# Optional password
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

pw = st.text_input("Enter Password (ask Reginald)", type="password", key="pw")
if st.button("Login"):
    if pw == "grizzly123":  # Change this password
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.error("Wrong password")

if not st.session_state.authenticated:
    st.stop()

# ====================== YOUR CORE FUNCTIONS ======================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def safe_get(url, timeout=30):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        st.warning(f"Error fetching {url}")
        return None

def extract_tables(html, base_title=""):
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    results = []
    for idx, table in enumerate(soup.find_all("table")):
        try:
            title = base_title
            prev = table.find_previous(["h1","h2","h3","h4","caption"])
            if prev:
                title = prev.get_text(strip=True)[:100]
            dfs = pd.read_html(StringIO(str(table)), header=0)
            if dfs:
                df = dfs[0].dropna(how="all", axis=1).dropna(how="all", axis=0)
                if not df.empty:
                    results.append((title, df))
        except:
            continue
    return results

def _parse_record(rec_str):
    if not rec_str or not isinstance(rec_str, str):
        return 0, 0, 0.5
    try:
        parts = [p.strip() for p in rec_str.replace("–","-").split("-")]
        w, l = int(parts[0]), int(parts[1])
        pct = w / (w + l) if (w + l) > 0 else 0.5
        return w, l, pct
    except:
        return 0, 0, 0.5

def rank_daily_picks(matchups):
    scored = []
    for m in matchups:
        name = m.get("matchup", "")
        if " @ " not in name:
            continue
        away, home = [x.strip() for x in name.split(" @ ", 1)]
        sections = m.get("sections", {})

        pred_away = pred_home = None
        for title, df in sections.get("power_ratings", {}).get("tables", []):
            if "power ratings" in str(title).lower():
                try:
                    for _, row in df.iterrows():
                        if "predictive" in str(row.iloc[0]).lower():
                            pred_away = float(str(row.iloc[1]).split()[0])
                            pred_home = float(str(row.iloc[2]).split()[0])
                except:
                    pass

        rl_ud_away = rl_ud_home = None
        for title, df in sections.get("situational_trends", {}).get("tables", []):
            if "run line" in str(title).lower():
                try:
                    for _, row in df.iterrows():
                        if "as underdog" in str(row.iloc[0]).lower():
                            rl_ud_away = str(row.iloc[1])
                            rl_ud_home = str(row.iloc[2])
                except:
                    pass

        if pred_away is None:
            continue

        for is_away in [True, False]:
            team = away if is_away else home
            opp = home if is_away else away
            pred = pred_away if is_away else pred_home
            opp_pred = pred_home if is_away else pred_away
            rl_ud = rl_ud_away if is_away else rl_ud_home

            if pred >= opp_pred - 0.01:
                continue

            score = 0.0
            if rl_ud:
                w, l, pct = _parse_record(rl_ud)
                score += (pct - 0.5) * 100
                if pct >= 0.57: score += 15
                if pct >= 0.61: score += 10
            edge = opp_pred - pred
            score += edge * 8

            scored.append({
                "team": team,
                "opponent": opp,
                "score": round(score, 1),
                "rl_record": rl_ud or "N/A"
            })
    scored.sort(key=lambda x: x["score"], reverse=True)
    seen = set()
    return [p for p in scored if not (p["team"] in seen or seen.add(p["team"]))][:12]

# ====================== MAIN APP ======================
date = st.date_input("Select Research Date", datetime.date.today())

if st.button("🚀 Run Full Research", type="primary", use_container_width=True):
    with st.spinner("Fetching data from TeamRankings, MLB, Rotowire..."):
        date_str = date.strftime("%Y-%m-%d")
        # Run your fetch functions here (simplified for Streamlit)
        st.success(f"✅ Research complete for {date_str}")

        # Placeholder for picks
        st.subheader("🔥 Top 6 +1.5 Run Line Picks")
        # In real version this would call rank_daily_picks
        st.info("Picks will appear here after full integration.")

st.sidebar.info("Share this link with your brother.\nPassword protected.")

st.caption("Built for Grizzly's Bet Cave")
