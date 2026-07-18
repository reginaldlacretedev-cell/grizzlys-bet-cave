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
    if pw == "grizzly123":
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.error("Wrong password")
if not st.session_state.authenticated:
    st.stop()

# ====================== YOUR FULL LOGIC ======================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
}

def safe_get(url, timeout=30):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        st.warning(f"Error fetching {url}")
        return None

def extract_tables(html, base_title=""):
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    results = []
    tables = soup.find_all("table")
    for idx, table in enumerate(tables):
        try:
            title = base_title
            prev_header = table.find_previous(["h1", "h2", "h3", "h4", "h5", "caption", "strong", "b"])
            if prev_header:
                title = prev_header.get_text(strip=True)[:120]
            dfs = pd.read_html(StringIO(str(table)), header=0, flavor="lxml")
            if dfs:
                df = dfs[0].dropna(how="all", axis=1).dropna(how="all", axis=0)
                if not df.empty and len(df.columns) > 1:
                    results.append((title or f"Table_{idx+1}", df))
        except Exception:
            continue
    return results

def _parse_record(rec_str):
    if not rec_str or not isinstance(rec_str, str):
        return 0, 0, 0.5
    rec_str = rec_str.strip().replace("–", "-")
    try:
        parts = [p for p in rec_str.split("-") if p.strip()]
        if len(parts) >= 2:
            w = int(parts[0])
            l = int(parts[1])
            total = w + l
            pct = w / total if total > 0 else 0.5
            return w, l, pct
    except Exception:
        pass
    return 0, 0, 0.5

def rank_daily_picks(matchups):
    """Your upgraded ranking"""
    scored = []
    for m in matchups:
        matchup_name = m.get("matchup", "")
        sections = m.get("sections", {})
        if " @ " not in matchup_name:
            continue
        away_name, home_name = [x.strip() for x in matchup_name.split(" @ ", 1)]

        pred_away = pred_home = None
        power_sec = sections.get("power_ratings", {})
        for title, df in power_sec.get("tables", []):
            if "team power ratings" in str(title).lower():
                try:
                    for _, row in df.iterrows():
                        row0 = str(row.iloc[0]).strip().lower()
                        val1 = str(row.iloc[1]).split()[0] if pd.notna(row.iloc[1]) else None
                        val2 = str(row.iloc[2]).split()[0] if len(row) > 2 and pd.notna(row.iloc[2]) else None
                        if "predictive" in row0:
                            pred_away = float(val1)
                            pred_home = float(val2)
                except:
                    continue

        rl_ud_away = rl_ud_home = None
        trends_sec = sections.get("situational_trends", {})
        for title, df in trends_sec.get("tables", []):
            if "run line" in str(title).lower():
                try:
                    for _, row in df.iterrows():
                        label = str(row.iloc[0]).strip().lower()
                        rec1 = str(row.iloc[1]) if len(row) > 1 else ""
                        rec2 = str(row.iloc[2]) if len(row) > 2 else ""
                        if "as underdog" in label:
                            rl_ud_away, rl_ud_home = rec1, rec2
                except:
                    continue

        if pred_away is None or pred_home is None:
            continue

        candidates = []
        for is_away in [True, False]:
            team = away_name if is_away else home_name
            opp = home_name if is_away else away_name
            pred = pred_away if is_away else pred_home
            opp_pred = pred_home if is_away else pred_away
            rl_ud = rl_ud_away if is_away else rl_ud_home

            is_underdog = pred < opp_pred - 0.01
            if not is_underdog:
                continue

            score = 0.0
            if rl_ud:
                w, l, pct = _parse_record(rl_ud)
                score += (pct - 0.50) * 100
                if (w + l) >= 25: score += 12
                if pct >= 0.570: score += 15
                if pct >= 0.610: score += 10

            edge = opp_pred - pred
            score += edge * 8

            candidates.append({
                "team": team,
                "opponent": opp,
                "score": round(score, 1),
                "rl_record": rl_ud
            })

        scored.extend(candidates)

    scored.sort(key=lambda x: x["score"], reverse=True)

    seen = set()
    unique = []
    for p in scored:
        if p["team"] not in seen:
            seen.add(p["team"])
            unique.append(p)
    return unique[:12]

# ====================== STREAMLIT UI ======================
date = st.date_input("Select Date", datetime.date.today())

if st.button("🚀 Run Research", type="primary", use_container_width=True):
    date_str = date.strftime("%Y-%m-%d")
    with st.spinner(f"Fetching real data for {date_str}..."):
        # Fetch matchups
        matchups = []
        html = safe_get(f"https://www.teamrankings.com/mlb/schedules/?date={date_str}")
        if html:
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/mlb/matchup/" in href:
                    display = a.get_text(strip=True)
                    matchups.append({"matchup": display or "Team vs Opponent"})

        picks = rank_daily_picks(matchups)
        
        st.success(f"✅ Research complete for {date_str} ({len(matchups)} matchups found)")

        st.subheader("🔥 Top 6 +1.5 Run Line Picks")
        if picks:
            for i, p in enumerate(picks[:6], 1):
                st.markdown(f"**{i}. {p['team']} +1.5** vs {p['opponent']}")
                st.write(f"   Score: {p['score']} | RL UD: {p.get('rl_record', 'N/A')}")
                st.divider()
            
            if len(picks) > 6:
                st.subheader("Honorable Mentions")
                for p in picks[6:9]:
                    st.write(f"- {p['team']} +1.5 vs {p['opponent']} (Score: {p['score']})")
        else:
            st.warning("No strong underdog picks found for this date. Try a different date.")

st.caption("Built for Grizzly's Bet Cave")
