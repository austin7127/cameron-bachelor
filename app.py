"""
Cameron's Bachelor Party — Location Voter
Each guest ranks the 8 activities by importance.
The app scores each destination and recommends the best fit.
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
from streamlit_sortables import sort_items

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cameron's Bachelor Party",
    page_icon="🥂",
    layout="centered",
)

# ── Earthy theme ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Background */
    .stApp { background-color: #F5F0E8; }

    /* Main title */
    h1 { color: #3D2B1F !important; font-family: Georgia, serif; }
    h2, h3 { color: #5C4A1E !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #E8DFC8;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #5C4A1E;
        font-weight: 600;
        border-radius: 8px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #8B6914 !important;
        color: white !important;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background-color: #8B6914;
        color: white;
        border: none;
        border-radius: 10px;
        font-size: 1rem;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #5C4A1E;
        color: white;
    }

    /* Text input */
    .stTextInput > div > div > input {
        background-color: #FDF8F0;
        border: 1.5px solid #C4A45A;
        border-radius: 8px;
        color: #3D2B1F;
    }

    /* Divider */
    hr { border-color: #C4A45A; }

    /* Metric */
    [data-testid="metric-container"] {
        background-color: #EDE4D0;
        border-radius: 10px;
        padding: 12px 20px;
        border: 1px solid #C4A45A;
    }

    /* Info/success/warning */
    .stAlert { border-radius: 10px; }

    /* Sortable items */
    .sortable-item {
        background-color: #EDE4D0 !important;
        border: 1.5px solid #C4A45A !important;
        border-radius: 8px !important;
        color: #000000 !important;
        font-weight: 600 !important;
        padding: 10px 14px !important;
        margin: 4px 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

ACTIVITIES = [
    "Fly Fishing",
    "Rock Climbing",
    "River Rafting",
    "Sport Shooting",
    "Pheasant Hunting",
    "Golf",
    "Gambling",
    "Dinners/Food Scene",
    "Bar/Party Scene",
]

LOCATION_SCORES = {
    "Moab, Utah": {
        "Fly Fishing":       2,
        "Rock Climbing":     3,
        "River Rafting":     3,
        "Sport Shooting":    2,
        "Pheasant Hunting":  1,
        "Golf":              2,
        "Gambling":          0,
        "Dinners/Food Scene":1,
        "Bar/Party Scene":   1,
    },
    "Scottsdale/Sedona, Arizona": {
        "Fly Fishing":       1,
        "Rock Climbing":     2,
        "River Rafting":     1,
        "Sport Shooting":    3,
        "Pheasant Hunting":  1,
        "Golf":              3,
        "Gambling":          1,
        "Dinners/Food Scene":3,
        "Bar/Party Scene":   3,
    },
    "Bozeman, Montana": {
        "Fly Fishing":       3,
        "Rock Climbing":     1,
        "River Rafting":     2,
        "Sport Shooting":    2,
        "Pheasant Hunting":  3,
        "Golf":              2,
        "Gambling":          0,
        "Dinners/Food Scene":2,
        "Bar/Party Scene":   2,
    },
}

LOCATION_DESCRIPTIONS = {
    "Moab, Utah": "World-class red rock climbing and desert landscape. Green River fly fishing, open shooting, and golf nearby.",
    "Scottsdale/Sedona, Arizona": "Desert landscape with Sedona climbing. Top-tier shooting ranges, premier golf, and hunting preserves.",
    "Bozeman, Montana": "World-famous fly fishing on the Madison and Gallatin Rivers. Premier pheasant hunting, shooting culture, and big sky scenery.",
}

LOCATION_EMOJI = {
    "Moab, Utah": "🏜️",
    "Scottsdale/Sedona, Arizona": "☀️",
    "Bozeman, Montana": "🏔️",
}

MEDAL = ["🥇", "🥈", "🥉"]

ACCOMMODATIONS = [
    "Luxury Hotel / Resort",
    "Vacation Rental House (VRBO/Airbnb)",
    "Boutique / Local Inn",
    "Glamping",
    "Camping",
]

BUDGET_OPTIONS = [
    "Under $400",
    "$400 to $600",
    "$600 to $800",
    "$800 to $1,000",
    "$1,000+",
]

TOTAL_GUESTS = 10

# ── Google Sheets connection ──────────────────────────────────────────────────

def get_credentials():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    return Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

def get_sheet():
    gc = gspread.authorize(get_credentials())
    return gc.open(st.secrets["sheet_name"]).sheet1

def get_stay_sheet():
    gc = gspread.authorize(get_credentials())
    wb = gc.open(st.secrets["sheet_name"])
    try:
        return wb.worksheet("stay_budget")
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title="stay_budget", rows=100, cols=5)
        ws.append_row(["timestamp", "name", "accommodation", "budget"])
        return ws

def load_votes() -> pd.DataFrame:
    sheet = get_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["timestamp", "name"] + ACTIVITIES)
    return pd.DataFrame(data)

def load_stay_votes() -> pd.DataFrame:
    sheet = get_stay_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["timestamp", "name", "accommodation", "budget"])
    return pd.DataFrame(data)

def save_vote(name: str, rankings: dict) -> None:
    sheet = get_sheet()
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name] + [rankings[a] for a in ACTIVITIES]
    sheet.append_row(row)

def save_stay_vote(name: str, accom_choice: str, budget: str) -> None:
    sheet = get_stay_sheet()
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, accom_choice, budget]
    sheet.append_row(row)


# ── Scoring logic ─────────────────────────────────────────────────────────────

def score_locations(votes_df: pd.DataFrame) -> dict:
    if votes_df.empty:
        return {loc: 0 for loc in LOCATION_SCORES}

    activity_weights = {}
    for activity in ACTIVITIES:
        if activity in votes_df.columns:
            activity_weights[activity] = sum(10 - int(r) for r in votes_df[activity] if r)
        else:
            activity_weights[activity] = 0

    scores = {}
    for location, loc_scores in LOCATION_SCORES.items():
        scores[location] = sum(
            activity_weights[activity] * loc_scores[activity]
            for activity in ACTIVITIES
        )

    return scores


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🥂 Cameron's Bachelor Party")
st.markdown("**Help decide where the crew is headed. Rank what matters most to you.**")
st.divider()

tab_vote, tab_results = st.tabs(["🗳️ Cast Your Vote", "📊 Results"])

# ── Vote tab ──────────────────────────────────────────────────────────────────

with tab_vote:
    # Track whether activity vote was just submitted
    if "activity_vote_submitted" not in st.session_state:
        st.session_state.activity_vote_submitted = False
    if "voter_name" not in st.session_state:
        st.session_state.voter_name = ""

    # ── Step 1: Activity ranking ──
    st.subheader("Step 1 — Rank the Activities")
    st.caption("Drag to reorder — top = most important to you, bottom = least important.")

    name = st.text_input("Your name", placeholder="e.g. Jake")
    st.markdown("")

    sorted_activities = sort_items(ACTIVITIES, direction="vertical", key="activity_sort_v2")

    st.markdown("")

    if not st.session_state.activity_vote_submitted:
        submitted = st.button("Submit Activity Vote", use_container_width=True, type="primary")

        if submitted:
            if not name.strip():
                st.warning("Please enter your name.")
            else:
                rankings = {activity: sorted_activities.index(activity) + 1 for activity in ACTIVITIES}
                try:
                    votes_df = load_votes()
                    existing_names = [n.lower() for n in votes_df["name"].tolist()] if not votes_df.empty else []
                    if name.strip().lower() in existing_names:
                        st.warning(f"A vote from **{name}** has already been submitted.")
                    else:
                        save_vote(name.strip(), rankings)
                        st.session_state.activity_vote_submitted = True
                        st.session_state.voter_name = name.strip()
                        st.rerun()
                except Exception as e:
                    st.error(f"Something went wrong saving your vote: {e}")

    # ── Step 2: Stay & Budget (auto-populates after activity vote) ──
    if st.session_state.activity_vote_submitted:
        st.success(f"Activity vote submitted! Thanks, {st.session_state.voter_name} 🤙")
        st.divider()
        st.subheader("Step 2 — Stay & Budget")
        st.caption("Almost done! Tell us how you'd like to stay and what budget works for you.")

        accom_choice = st.radio(
            "**Where would you prefer to stay?**",
            ACCOMMODATIONS,
            horizontal=False,
        )

        st.markdown("")
        budget = st.radio(
            "**Your comfortable per-person budget for the trip:**",
            BUDGET_OPTIONS,
            horizontal=False,
        )

        st.markdown("")
        stay_submitted = st.button("Submit Stay & Budget", use_container_width=True, type="primary")

        if stay_submitted:
            try:
                stay_df = load_stay_votes()
                existing = [n.lower() for n in stay_df["name"].tolist()] if not stay_df.empty else []
                if st.session_state.voter_name.lower() in existing:
                    st.warning("Stay & budget preference already submitted.")
                else:
                    save_stay_vote(st.session_state.voter_name, accom_choice, budget)
                    st.success("All done! Your full response has been recorded. 🎉")
                    st.session_state.activity_vote_submitted = False
                    st.session_state.voter_name = ""
            except Exception as e:
                st.error(f"Something went wrong saving your stay preference: {e}")

# ── Results tab ───────────────────────────────────────────────────────────────

with tab_results:
    st.subheader("Live Results")

    try:
        votes_df = load_votes()
        count = len(votes_df)

        # Vote progress
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Votes Submitted", f"{count} / {TOTAL_GUESTS}")
        with col2:
            pct = int(count / TOTAL_GUESTS * 100)
            st.metric("Participation", f"{pct}%")

        st.markdown("")

        if count == 0:
            st.info("No votes yet — share the link with the crew!")
        else:
            scores = score_locations(votes_df)
            score_df = pd.DataFrame({
                "Location": list(scores.keys()),
                "Score": list(scores.values()),
            }).sort_values("Score", ascending=False).reset_index(drop=True)

            # ── Leaderboard ──
            st.markdown("### 📍 Destination Leaderboard")
            max_score = score_df["Score"].max()

            for i, row in score_df.iterrows():
                loc = row["Location"]
                score = row["Score"]
                pct_bar = int(score / max_score * 100) if max_score > 0 else 0
                emoji = LOCATION_EMOJI.get(loc, "📍")
                medal = MEDAL[i] if i < 3 else ""

                st.markdown(f"""
<div style="background-color:#EDE4D0; border:1.5px solid #C4A45A; border-radius:12px; padding:16px 20px; margin-bottom:12px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:1.1rem; font-weight:700; color:#3D2B1F;">{medal} {emoji} {loc}</span>
        <span style="font-size:1.2rem; font-weight:800; color:#8B6914;">{score} pts</span>
    </div>
    <div style="background-color:#D6C9A8; border-radius:6px; height:10px; margin-top:10px;">
        <div style="background-color:#8B6914; width:{pct_bar}%; height:10px; border-radius:6px;"></div>
    </div>
    <div style="color:#6B5A3E; font-size:0.85rem; margin-top:8px;">{LOCATION_DESCRIPTIONS[loc]}</div>
</div>
""", unsafe_allow_html=True)

            # ── Winner callout ──
            winner = score_df.iloc[0]["Location"]
            runner_up = score_df.iloc[1]["Location"]
            winner_score = score_df.iloc[0]["Score"]
            runner_up_score = score_df.iloc[1]["Score"]
            margin = round((winner_score - runner_up_score) / winner_score * 100, 1) if winner_score > 0 else 0

            st.markdown(f"""
<div style="background-color:#5C4A1E; border-radius:14px; padding:20px 24px; margin-top:8px; text-align:center;">
    <div style="color:#F5DFA0; font-size:0.95rem; font-weight:600; letter-spacing:1px;">GROUP RECOMMENDATION</div>
    <div style="color:white; font-size:1.8rem; font-weight:800; margin:6px 0;">{LOCATION_EMOJI.get(winner, "")} {winner}</div>
    <div style="color:#D6C9A8; font-size:0.9rem;">Leading {runner_up} by {margin}% based on group priorities</div>
</div>
""", unsafe_allow_html=True)

            st.markdown("")

            # ── Activity priorities ──
            st.markdown("### 🥂 What the Group Cares About Most")
            activity_weights = {}
            for activity in ACTIVITIES:
                if activity in votes_df.columns:
                    activity_weights[activity] = sum(10 - int(r) for r in votes_df[activity] if r)
                else:
                    activity_weights[activity] = 0

            sorted_weights = sorted(activity_weights.items(), key=lambda x: x[1], reverse=True)
            max_weight = sorted_weights[0][1] if sorted_weights else 1

            for activity, weight in sorted_weights:
                bar_pct = int(weight / max_weight * 100)
                st.markdown(f"""
<div style="margin-bottom:8px;">
    <div style="display:flex; justify-content:space-between; color:#3D2B1F; font-size:0.9rem; margin-bottom:3px;">
        <span style="font-weight:600;">{activity}</span>
        <span style="color:#8B6914;">{weight} pts</span>
    </div>
    <div style="background-color:#D6C9A8; border-radius:6px; height:8px;">
        <div style="background-color:#6B8C42; width:{bar_pct}%; height:8px; border-radius:6px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

            if count < TOTAL_GUESTS:
                st.markdown("")
                st.caption(f"Results update live as votes come in. {TOTAL_GUESTS - count} vote(s) still pending.")

            # ── Stay & Budget results ──
            st.markdown("")
            st.markdown("### 🏕️ Stay & Budget")
            try:
                stay_df = load_stay_votes()
                if stay_df.empty:
                    st.info("No stay & budget votes yet.")
                else:
                    stay_count = len(stay_df)
                    st.caption(f"{stay_count} of {TOTAL_GUESTS} stay & budget responses")

                    # Accommodation leaderboard
                    st.markdown("#### Accommodation Preference")
                    if "accommodation" in stay_df.columns:
                        accom_counts = stay_df["accommodation"].value_counts()
                        sorted_accom = [(a, accom_counts.get(a, 0)) for a in ACCOMMODATIONS]
                        sorted_accom = sorted(sorted_accom, key=lambda x: x[1], reverse=True)
                        max_accom = sorted_accom[0][1] if sorted_accom else 1

                        for i, (accom, c) in enumerate(sorted_accom):
                            bar_pct = int(c / stay_count * 100) if stay_count > 0 else 0
                            medal = MEDAL[i] if i < 3 and c > 0 else ""
                            st.markdown(f"""
<div style="margin-bottom:8px;">
    <div style="display:flex; justify-content:space-between; color:#3D2B1F; font-size:0.9rem; margin-bottom:3px;">
        <span style="font-weight:600;">{medal} {accom}</span>
        <span style="color:#8B6914;">{c} vote{'s' if c != 1 else ''}</span>
    </div>
    <div style="background-color:#D6C9A8; border-radius:6px; height:8px;">
        <div style="background-color:#8B6914; width:{bar_pct}%; height:8px; border-radius:6px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

                    # Budget distribution
                    st.markdown("")
                    st.markdown("#### Budget Range")
                    if "budget" in stay_df.columns:
                        budget_counts = stay_df["budget"].value_counts()
                        for option in BUDGET_OPTIONS:
                            c = budget_counts.get(option, 0)
                            bar_pct = int(c / stay_count * 100) if stay_count > 0 else 0
                            st.markdown(f"""
<div style="margin-bottom:8px;">
    <div style="display:flex; justify-content:space-between; color:#3D2B1F; font-size:0.9rem; margin-bottom:3px;">
        <span style="font-weight:600;">{option}</span>
        <span style="color:#8B6914;">{c} vote{'s' if c != 1 else ''}</span>
    </div>
    <div style="background-color:#D6C9A8; border-radius:6px; height:8px;">
        <div style="background-color:#6B8C42; width:{bar_pct}%; height:8px; border-radius:6px;"></div>
    </div>
</div>
""", unsafe_allow_html=True)

            except Exception as e:
                st.warning(f"Could not load stay & budget results: {e}")

            # ── Raw votes ──
            with st.expander("See all votes"):
                display_df = votes_df[["name"] + ACTIVITIES].rename(columns={"name": "Name"})
                st.dataframe(display_df, use_container_width=True)

    except Exception as e:
        st.error(f"Could not load results: {e}")
