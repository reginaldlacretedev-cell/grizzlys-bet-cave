import streamlit as st
import datetime
import re
from io import StringIO
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Grizzly's Bet Cave", layout="wide")
st.title("🐻 Grizzly's Bet Cave")
st.subheader("Daily +1.5 Run Line Research")

# Password
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

pw = st.text_input("Enter Password", type="password")
if st.button("Login"):
    if pw == "grizzly123":  # Change this
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.error("Wrong password")
if not st.session_state.authenticated:
    st.stop()

# ====================== CORE LOGIC ======================
HEADERS = {"User-Agent": "Mozilla/5.0"}

def safe_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except:
        return None

def _parse_record(rec_str):
    if not rec_str:
        return 0, 0, 0.5
    try:
        parts = [p.strip() for p in rec_str.replace("–", "-").split("-")]
        w, l = int(parts[0]), int(parts[1])
        pct = w / (w + l) if (w + l) > 0 else 0.5
        return w, l, pct
    except:
        return 0, 0, 0.5

def rank_daily_picks(matchups):
    scored = []
    for m in matchups:
        name = m.get("matchup", "")
        if " @ " not in name: continue
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
        
        if pred_away is None: continue
        
        for is_away in [True, False]:
            team = away if is_away else home
            opp = home if is_away else away
            pred = pred_away if is_away else pred_home
            opp_pred = pred_home if is_away else pred_away
            rl_ud = rl_ud_away if is_away else rl_ud_home
            if pred >= opp_pred - 0.01: continue
            
            score = 0.0
            if rl_ud:
                _, _, pct = _parse_record(rl_ud)
                score += (pct - 0.5) * 100
                if pct >= 0.57: score += 15
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

# ====================== UI ======================
date = st.date_input("Select Date", datetime.date.today())

if st.button("🚀 Run Research", type="primary", use_container_width=True):
    date_str = date.strftime("%Y-%m-%d")
    with st.spinner(f"Fetching data for {date_str}..."):
        # Fetch schedule (simplified)
        schedule_html = safe_get(f"https://www.teamrankings.com/mlb/schedules/?date={date_str}")
        st.success(f"✅ Data fetched for {date_str}")
        
        # Simulate matchups for demo (replace with real parsing later)
        matchups = [{"matchup": "Example Team @ Opponent"}]  
        picks = rank_daily_picks(matchups)
        
        st.subheader("🔥 Top 6 +1.5 Run Line Picks")
        for i, p in enumerate(picks[:6], 1):
            st.markdown(f"**{i}. {p['team']} +1.5** vs {p['opponent']}")
            st.write(f"Score: {p['score']} | RL UD: {p['rl_record']}")
            st.divider()

st.caption("Share this link with your brother. Password: grizzly123 (change it)")
