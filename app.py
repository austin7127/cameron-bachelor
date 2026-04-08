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

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Cameron's Bachelor Party",
    page_icon="🎯",
    layout="centered",
)

# ── Constants ─────────────────────────────────────────────────────────────────

ACTIVITIES = [
    "Fly Fishing",
    "Rock Climbing",
    "Sport Shooting",
    "Pheasant Hunting",
    "Golf",
    "Gambling",
    "Dinners/Food Scene",
    "Bar/Party Scene",
]

# How well each location supports each activity (0-3)
# 3 = excellent, 2 = good, 1 = limited, 0 = not available
LOCATION_SCORES = {
    "Moab, Utah": {
        "Fly Fishing":       2,
        "Rock Climbing":     3,
        "Sport Shooting":    2,
        "Pheasant Hunting":  1,
        "Golf":              2,
        "Gambling":          0,
        "Dinners/Food Scene":1,
        "Bar/Party Scene":   1,
    },
    "Scottsdale/Sedona, Arizona": {
        "Fly Fishing":       1,
        "Rock Climbing":     3,
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

TOTAL_GUESTS = 10

# ── Google Sheets connection ──────────────────────────────────────────────────

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    gc = gspread.authorize(creds)
    return gc.open(st.secrets["sheet_name"]).sheet1


def load_votes() -> pd.DataFrame:
    sheet = get_sheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["timestamp", "name"] + ACTIVITIES)
    return pd.DataFrame(data)


def save_vote(name: str, rankings: dict) -> None:
    sheet = get_sheet()
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name] + [rankings[a] for a in ACTIVITIES]
    sheet.append_row(row)


# ── Scoring logic ─────────────────────────────────────────────────────────────

def score_locations(votes_df: pd.DataFrame) -> dict:
    """
    Convert each person's rank (1=most important) to a weight (rank 1 = 5 pts, rank 5 = 1 pt).
    Sum weights across all voters per activity.
    Multiply by each location's activity score.
    """
    if votes_df.empty:
        return {loc: 0 for loc in LOCATION_SCORES}

    # Activity weights: sum of (6 - rank) across all voters
    activity_weights = {}
    for activity in ACTIVITIES:
        if activity in votes_df.columns:
            activity_weights[activity] = sum(9 - int(r) for r in votes_df[activity] if r)
        else:
            activity_weights[activity] = 0

    # Score each location
    scores = {}
    for location, loc_scores in LOCATION_SCORES.items():
        scores[location] = sum(
            activity_weights[activity] * loc_scores[activity]
            for activity in ACTIVITIES
        )

    return scores


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🎯 Cameron's Bachelor Party")
st.markdown("**Vote for your preferred destination by ranking the activities below.**")
st.divider()

tab_vote, tab_results = st.tabs(["🗳️ Cast Your Vote", "📊 Results"])

# ── Vote tab ──────────────────────────────────────────────────────────────────

with tab_vote:
    st.subheader("Rank the Activities")
    st.caption("1 = Most important to you, 8 = Least important. Each rank can only be used once.")

    name = st.text_input("Your name", placeholder="e.g. Jake")

    st.markdown("---")

    cols = st.columns(2)
    rankings = {}
    for i, activity in enumerate(ACTIVITIES):
        col = cols[i % 2]
        with col:
            rankings[activity] = st.selectbox(
                activity,
                options=[1, 2, 3, 4, 5, 6, 7, 8],
                key=f"rank_{activity}",
            )

    st.markdown("---")
    submitted = st.button("Submit Vote", use_container_width=True, type="primary")

    if submitted:
        if not name.strip():
            st.warning("Please enter your name.")
        elif len(set(rankings.values())) < len(ACTIVITIES):
            st.warning("Each activity must have a unique rank (1–5). No duplicates.")
        else:
            try:
                votes_df = load_votes()
                existing_names = [n.lower() for n in votes_df["name"].tolist()] if not votes_df.empty else []
                if name.strip().lower() in existing_names:
                    st.warning(f"A vote from **{name}** has already been submitted.")
                else:
                    save_vote(name.strip(), rankings)
                    st.success(f"Vote submitted! Thanks, {name.strip()}.")
                    votes_df = load_votes()
                    count = len(votes_df)
                    st.info(f"**{count} of {TOTAL_GUESTS}** crew members have voted.")
            except Exception as e:
                st.error(f"Something went wrong saving your vote: {e}")

# ── Results tab ───────────────────────────────────────────────────────────────

with tab_results:
    st.subheader("Live Results")

    try:
        votes_df = load_votes()
        count = len(votes_df)

        st.metric("Votes submitted", f"{count} / {TOTAL_GUESTS}")

        if count == 0:
            st.info("No votes yet. Share the link with the crew!")
        else:
            # Activity importance chart
            st.markdown("#### What the group cares about most")
            activity_weights = {}
            for activity in ACTIVITIES:
                if activity in votes_df.columns:
                    activity_weights[activity] = sum(9 - int(r) for r in votes_df[activity] if r)
                else:
                    activity_weights[activity] = 0

            weight_df = pd.DataFrame({
                "Activity": list(activity_weights.keys()),
                "Group Importance Score": list(activity_weights.values()),
            }).sort_values("Group Importance Score", ascending=False)

            st.bar_chart(weight_df.set_index("Activity"))

            # Location scores
            st.markdown("#### Location scores")
            scores = score_locations(votes_df)
            score_df = pd.DataFrame({
                "Location": list(scores.keys()),
                "Score": list(scores.values()),
            }).sort_values("Score", ascending=False)

            st.bar_chart(score_df.set_index("Location"))

            # Winner
            winner = score_df.iloc[0]["Location"]
            winner_score = score_df.iloc[0]["Score"]
            runner_up = score_df.iloc[1]["Location"]
            runner_up_score = score_df.iloc[1]["Score"]
            margin = round((winner_score - runner_up_score) / winner_score * 100, 1)

            st.markdown("---")
            st.markdown(f"## 🏆 Recommended Destination")
            st.markdown(f"# {winner}")
            st.markdown(LOCATION_DESCRIPTIONS[winner])
            st.markdown(f"*Leading {runner_up} by {margin}% based on group preferences.*")

            if count < TOTAL_GUESTS:
                st.caption(f"Results update live. {TOTAL_GUESTS - count} vote(s) still pending.")

            # Raw votes table (expandable)
            with st.expander("See all votes"):
                display_df = votes_df[["name"] + ACTIVITIES].rename(columns={"name": "Name"})
                st.dataframe(display_df, use_container_width=True)

    except Exception as e:
        st.error(f"Could not load votes: {e}")
