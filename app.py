
from pathlib import Path
import html
import json

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"

st.set_page_config(
    page_title="CLUTCH IQ | Cricket Intelligence",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# DARK THEME — PREMIUM SPORTS ANALYTICS
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #080D16;
    --panel: #101927;
    --panel2: #131F30;
    --border: #233248;
    --text: #F2F5FA;
    --muted: #91A0B5;
    --accent: #D6FF5F;
    --accent2: #A9D63E;
    --orange: #FF9D5C;
    --red: #FF6878;
}

.stApp {
    background:
        radial-gradient(ellipse at 10% 0%, rgba(91,126,58,.13), transparent 32%),
        radial-gradient(ellipse at 95% 10%, rgba(48,87,130,.13), transparent 35%),
        var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
}

header[data-testid="stHeader"] {
    background: rgba(8,13,22,.85);
}

.block-container {
    max-width: 1440px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
}

h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--text) !important;
}

p, li, label, span {
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stCaptionContainer"] {
    color: var(--muted);
}

[data-testid="stTabs"] button {
    color: var(--muted);
    font-weight: 600;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

[data-testid="stRadio"] label,
[data-testid="stSelectbox"] label {
    color: var(--muted) !important;
    font-weight: 600;
}

div[data-baseweb="select"] > div {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
}

.stRadio > div {
    gap: 1.2rem;
}

.stRadio label {
    color: var(--text) !important;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #142033, #0F1928);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 20px;
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-size: .82rem;
}

[data-testid="stMetricValue"] {
    color: var(--accent) !important;
    font-family: 'Space Grotesk', sans-serif;
}

.stButton button {
    border-radius: 9px;
    border: 1px solid var(--border);
    background: var(--panel);
    color: var(--text);
}

hr {
    border-color: var(--border);
}

.hero {
    background:
        linear-gradient(110deg, rgba(214,255,95,.09), transparent 48%),
        linear-gradient(135deg, #142235, #0D1725);
    border: 1px solid #304257;
    border-radius: 20px;
    padding: 34px 38px;
    margin-bottom: 26px;
    position: relative;
    overflow: hidden;
}

.hero:after {
    content: "🏏";
    position: absolute;
    right: 55px;
    top: 12px;
    font-size: 100px;
    opacity: .09;
    transform: rotate(-18deg);
}

.hero-kicker {
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 3px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    margin-bottom: 12px;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    color: #F6F8FC;
    font-size: clamp(36px, 5vw, 55px);
    font-weight: 700;
    letter-spacing: -2px;
    line-height: 1.05;
}

.hero-subtitle {
    color: #A8B6C9;
    font-size: 15px;
    margin-top: 13px;
    max-width: 720px;
    line-height: 1.7;
}

.section-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 23px;
    font-weight: 700;
    color: var(--text);
    margin: 8px 0 5px 0;
}

.section-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 20px;
}

.player-card {
    display: grid;
    grid-template-columns: 58px minmax(130px, 1.6fr) repeat(3, minmax(75px, .8fr));
    align-items: center;
    gap: 12px;
    background: linear-gradient(110deg, #142033, #101927);
    border: 1px solid #26364B;
    border-radius: 13px;
    padding: 15px 18px;
    margin-bottom: 9px;
    transition: .2s ease;
}

.player-card:hover {
    border-color: #A8CF4C;
    transform: translateY(-2px);
    background: #17263A;
}

.player-card.top {
    border-color: rgba(214,255,95,.42);
    background: linear-gradient(110deg, rgba(214,255,95,.10), #111C2B 65%);
}

.player-rank {
    font-family: 'DM Mono', monospace;
    font-size: 21px;
    font-weight: 500;
    color: #7D8DA3;
}

.player-rank.gold { color: #F8D878; }
.player-rank.silver { color: #C3D1E1; }
.player-rank.bronze { color: #D99B71; }

.player-name {
    color: #F4F7FB;
    font-size: 15px;
    font-weight: 700;
}

.player-id {
    color: #718198;
    font-size: 10px;
    font-family: 'DM Mono', monospace;
    margin-top: 3px;
}

.player-stat-label {
    color: #8191A8;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .8px;
}

.player-stat-value {
    color: #E9EFF7;
    font-family: 'DM Mono', monospace;
    font-size: 14px;
    margin-top: 4px;
}

.player-stat-value.highlight {
    color: var(--accent);
    font-weight: 600;
}

.leaderboard-head {
    display: grid;
    grid-template-columns: 58px minmax(130px, 1.6fr) repeat(3, minmax(75px, .8fr));
    gap: 12px;
    padding: 0 18px 10px 18px;
    color: #7E8EA5;
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 1px;
}

.info-card {
    background: linear-gradient(145deg, #142033, #0F1928);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 21px;
    height: 100%;
}

.info-number {
    font-family: 'DM Mono', monospace;
    color: var(--accent);
    font-size: 12px;
    letter-spacing: 1px;
    margin-bottom: 12px;
}

.info-title {
    color: #F0F4FA;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 9px;
}

.info-text {
    color: #9BAAC0;
    font-size: 13px;
    line-height: 1.75;
}

.formula {
    background: #0A111D;
    border: 1px solid #26364B;
    border-left: 3px solid var(--accent);
    border-radius: 9px;
    padding: 15px 18px;
    color: #E4EDFA;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    overflow-x: auto;
    margin: 12px 0 18px 0;
}

.badge {
    display: inline-block;
    border: 1px solid rgba(214,255,95,.35);
    background: rgba(214,255,95,.09);
    color: var(--accent);
    border-radius: 30px;
    padding: 5px 11px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.footer {
    color: #718198;
    font-size: 11px;
    text-align: center;
    padding-top: 28px;
    border-top: 1px solid var(--border);
    margin-top: 45px;
}

@media(max-width: 750px) {
    .player-card {
        grid-template-columns: 35px 1fr 1fr;
        gap: 8px;
    }
    .player-card .extra-stat {
        display: none;
    }
    .leaderboard-head {
        grid-template-columns: 35px 1fr 1fr;
    }
    .leaderboard-head .extra-stat {
        display: none;
    }
    .hero {
        padding: 25px 22px;
    }
    .hero:after {
        right: 12px;
        font-size: 65px;
    }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA HELPERS
# ============================================================

def load_csv(filename):
    path = OUT / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_number(value, digits=1):
    try:
        if pd.isna(value):
            return "—"
        return f"{float(value):,.{digits}f}"
    except (ValueError, TypeError):
        return "—"


def safe_int(value):
    try:
        if pd.isna(value):
            return "—"
        return f"{int(float(value)):,}"
    except (ValueError, TypeError):
        return "—"


def safe_text(value):
    if pd.isna(value):
        return "Unknown"
    return html.escape(str(value))


def threshold_description(level):
    descriptions = {
        "relaxed": "Broader player coverage",
        "current": "Balanced evidence and coverage",
        "strict": "Higher experience requirements",
    }
    return descriptions.get(level, "")


def render_player_card(row, index):
    rank = int(row.get("rank", index + 1))
    name = safe_text(row.get("player_name", "Unknown Player"))
    pid = safe_text(row.get("player_id", "—"))

    rank_class = ""
    if rank == 1:
        rank_class = "gold"
    elif rank == 2:
        rank_class = "silver"
    elif rank == 3:
        rank_class = "bronze"

    top_class = "top" if rank == 1 else ""

    pressure_matches = safe_int(row.get("pressure_matches"))
    normal_matches = safe_int(row.get("normal_matches"))
    pressure_balls = safe_int(row.get("pressure_balls"))
    pressure_rate = safe_number(row.get("pressure_rate"), 2)
    normal_rate = safe_number(row.get("normal_rate"), 2)
    lift = safe_number(row.get("eb_lift", row.get("raw_lift")), 2)
    confidence = safe_number(
        row.get("bootstrap_prob_positive", float("nan")) * 100, 0
    )

    st.markdown(f"""
    <div class="player-card {top_class}">
        <div class="player-rank {rank_class}">#{rank:02d}</div>
        <div>
            <div class="player-name">{name}</div>
            <div class="player-id">PLAYER ID · {pid}</div>
        </div>
        <div>
            <div class="player-stat-label">Pressure lift</div>
            <div class="player-stat-value highlight">{lift}</div>
        </div>
        <div class="extra-stat">
            <div class="player-stat-label">Pressure matches</div>
            <div class="player-stat-value">{pressure_matches}</div>
        </div>
        <div class="extra-stat">
            <div class="player-stat-label">Positive bootstrap</div>
            <div class="player-stat-value">{confidence}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# HERO
# ============================================================

st.markdown("""
<div class="hero">
    <div class="hero-kicker">Cricket performance intelligence · 2022–2026</div>
    <div class="hero-title">CLUTCH IQ</div>
    <div class="hero-subtitle">
        Measuring performance when the game is on the line.
        An evidence-driven cricket analytics framework combining
        dynamic match pressure, win-probability leverage, resource scarcity
        and role-specific player performance.
    </div>
    <div style="margin-top:20px">
        <span class="badge">Hybrid Dynamic Pressure Intelligence</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# NAVIGATION
# ============================================================

tab_rank, tab_robust, tab_method = st.tabs([
    "🏆  LEADERBOARDS",
    "📊  ROBUSTNESS",
    "🧠  METHODOLOGY",
])


# ============================================================
# TAB 1 — LEADERBOARDS
# ============================================================

with tab_rank:

    st.markdown('<div class="section-heading">Pressure Performance Rankings</div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="section-subtitle">
        Top 10 players ranked by their performance advantage in high-pressure
        situations relative to their normal-performance baseline.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([1.3, 1])

    with c1:
        role_choice = st.radio(
            "PLAYER CATEGORY",
            ["Batters", "Bowlers"],
            horizontal=True,
            label_visibility="collapsed",
        )

    with c2:
        eligibility = st.selectbox(
            "ELIGIBILITY STANDARD",
            ["Current", "Relaxed", "Strict"],
            index=0,
            format_func=lambda x: f"{x} · {threshold_description(x.lower())}",
        )

    role = role_choice.lower()
    level = eligibility.lower()

    ranking_file = OUT / f"top10_{role}_{level}.csv"

    if ranking_file.exists():
        ranking = pd.read_csv(ranking_file)

        if ranking.empty:
            st.warning("No players satisfy the selected eligibility requirements.")
        else:
            # Summary metrics
            total_players = len(ranking)
            best_player = ranking.iloc[0]["player_name"]
            best_lift = ranking.iloc[0].get(
                "eb_lift", ranking.iloc[0].get("raw_lift", 0)
            )

            pressure_matches_total = ranking["pressure_matches"].sum()
            average_matches = ranking["pressure_matches"].mean()

            m1, m2, m3, m4 = st.columns(4)

            m1.metric("Ranked players", total_players)
            m2.metric("Top performer", str(best_player))
            m3.metric("Top pressure lift", safe_number(best_lift, 2))
            m4.metric("Avg. pressure matches", safe_number(average_matches, 1))

            st.markdown("---")

            st.markdown(
                f'<div class="section-heading">Top 10 {role_choice}</div>',
                unsafe_allow_html=True,
            )

            st.markdown("""
            <div class="leaderboard-head">
                <div>Rank</div>
                <div>Player</div>
                <div>EB pressure lift</div>
                <div class="extra-stat">Pressure matches</div>
                <div class="extra-stat">Positive bootstrap</div>
            </div>
            """, unsafe_allow_html=True)

            for i, row in ranking.iterrows():
                render_player_card(row, i)

            # Expandable detailed statistics
            with st.expander("VIEW DETAILED PLAYER STATISTICS"):
                detail_columns = [
                    "rank", "player_name", "pressure_matches",
                    "normal_matches", "pressure_balls", "normal_balls",
                    "pressure_rate", "normal_rate", "raw_lift", "eb_lift",
                    "bootstrap_prob_positive", "bootstrap_ci_low",
                    "bootstrap_ci_high",
                ]
                available = [x for x in detail_columns if x in ranking.columns]
                st.dataframe(
                    ranking[available],
                    use_container_width=True,
                    hide_index=True,
                )

            st.caption(
                "EB pressure lift is a shrinkage-adjusted performance difference. "
                "Positive bootstrap probability represents the proportion of "
                "bootstrap estimates above zero."
            )

    else:
        st.info(
            f"No ranking file found for {role_choice} under {eligibility} "
            "eligibility. Run the ranking pipeline first."
        )


# ============================================================
# TAB 2 — THRESHOLD ROBUSTNESS
# ============================================================

with tab_robust:

    st.markdown(
        '<div class="section-heading">Ranking Stability & Robustness</div>',
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="section-subtitle">
        We test whether the leading players remain competitive when the minimum
        evidence requirements become more demanding.
    </div>
    """, unsafe_allow_html=True)

    threshold_data = load_csv("threshold_sensitivity.csv")

    if not threshold_data.empty:

        for role in ["batters", "bowlers"]:
            subset = threshold_data[threshold_data["role"] == role]

            if subset.empty:
                continue

            st.markdown(f"### {role.title()}")

            cols = st.columns(3)

            for col, level in zip(cols, ["relaxed", "current", "strict"]):
                record = subset[subset["threshold"] == level]

                if not record.empty:
                    row = record.iloc[0]
                    with col:
                        st.metric(
                            level.title(),
                            f'{int(row["top10_count"])} / 10',
                            f'{int(row["overlap_with_current"])} overlap with Current',
                        )

        st.markdown("---")
        st.markdown("### Threshold comparison")

        st.dataframe(
            threshold_data,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### What do the three standards mean?")

        a, b, c = st.columns(3)

        with a:
            st.markdown("""
            <div class="info-card">
                <div class="info-number">01 · RELAXED</div>
                <div class="info-title">Broader coverage</div>
                <div class="info-text">
                    Requires at least 5 pressure matches, 5 normal matches,
                    40 pressure balls and 75 normal balls. It explores a
                    wider pool of players.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with b:
            st.markdown("""
            <div class="info-card">
                <div class="info-number">02 · CURRENT</div>
                <div class="info-title">Balanced evidence</div>
                <div class="info-text">
                    Requires at least 8 pressure matches, 8 normal matches,
                    60 pressure balls and 100 normal balls. This is the
                    primary working standard.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c:
            st.markdown("""
            <div class="info-card">
                <div class="info-number">03 · STRICT</div>
                <div class="info-title">Higher experience</div>
                <div class="info-text">
                    Requires at least 12 pressure matches, 12 normal matches,
                    100 pressure balls and 150 normal balls. It tests
                    robustness among more experienced players.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.caption(
            "These thresholds are initial methodological choices. "
            "Their suitability should be assessed through sample coverage "
            "and ranking stability."
        )

    else:
        st.info("Run Phase 5 to generate threshold_sensitivity.csv.")


# ============================================================
# TAB 3 — METHODOLOGY
# ============================================================

with tab_method:

    st.markdown(
        '<div class="section-heading">Understanding CLUTCH IQ</div>',
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="section-subtitle">
        The concepts, mathematical framework and statistical safeguards
        behind our pressure-performance rankings.
    </div>
    """, unsafe_allow_html=True)

    # WHAT IS PRESSURE?
    st.markdown("### What is pressure in cricket?")

    st.markdown("""
    Pressure is the difficulty and consequence of a match situation
    from the perspective of the player executing the next delivery.

    A batter chasing 45 runs from 24 balls with only three wickets remaining
    faces a different situation from a batter scoring freely with seven
    wickets and 90 balls remaining.

    Similarly, a bowler defending a small total in the final overs faces
    a different level of responsibility from a bowler operating during
    a comfortable middle-over phase.

    CLUTCH IQ does not claim to measure a player's psychological state.
    It measures **observable situational pressure and role-specific
    performance under that pressure**.
    """)

    st.markdown("---")

    # HDPI
    st.markdown("### 1. Hybrid Dynamic Pressure Intelligence (HDPI)")

    st.markdown("""
    HDPI combines five dimensions to estimate the pressure associated
    with a delivery's pre-delivery match state.
    """)

    components = [
        (
            "01",
            "Match-State Difficulty (MSD)",
            "Measures the difficulty of the current situation using "
            "required scoring pressure, current scoring position and "
            "wickets remaining. First-innings situations use the "
            "historical par-score deficit.",
            "25%",
        ),
        (
            "02",
            "Win-Probability Leverage (WPL)",
            "Measures the expected absolute movement in batting-team "
            "win probability across possible next-delivery outcomes. "
            "It identifies states where the next ball can meaningfully "
            "change the match outlook.",
            "30%",
        ),
        (
            "03",
            "Resource Scarcity Index (RSI)",
            "Measures how limited the remaining scoring resources are, "
            "considering the remaining legal balls and wickets.",
            "20%",
        ),
        (
            "04",
            "Situational Stress Index (SSI)",
            "Captures recent wicket losses, recovery requirements, "
            "partnership dependency and critical-over urgency.",
            "15%",
        ),
        (
            "05",
            "Phase & Execution Pressure (PEP)",
            "Accounts for innings progression and the severity of the "
            "current situation. The death overs are not automatically "
            "treated as the most pressurised situations.",
            "10%",
        ),
    ]

    for number, title, description, weight in components:
        st.markdown(f"""
        <div class="info-card" style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;gap:15px">
                <div>
                    <div class="info-number">{number} · PRESSURE DIMENSION</div>
                    <div class="info-title">{title}</div>
                </div>
                <div style="color:#D6FF5F;font-family:'DM Mono';font-size:20px">
                    {weight}
                </div>
            </div>
            <div class="info-text">{description}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("**Combined pressure equation**")

    st.markdown("""
    <div class="formula">
    HDPI = 100 × (0.25 MSD + 0.30 WPL + 0.20 RSI + 0.15 SSI + 0.10 PEP)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    All five dimensions are normalized to a 0–1 scale before combination.
    The weights are initial design choices and should be tested through
    ablation and sensitivity analysis.
    """)

    st.markdown("---")

    # WPL
    st.markdown("### 2. Win-Probability Leverage")

    st.markdown("""
    WPL evaluates the possible impact of the next delivery.

    First, the model estimates the batting team's win probability before
    the delivery. It then considers possible outcomes, simulates the
    resulting match states and estimates win probability after each
    simulated outcome.

    The calculation uses the probability-weighted absolute change:
    """)

    st.markdown("""
    <div class="formula">
    WPL(S) = Σ P(o | S) × | WP(Sₒ) − WP(S) |
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    Here:

    - **S:** Current pre-delivery match state.
    - **o:** A possible delivery outcome.
    - **P(o | S):** Probability of that outcome given the current state.
    - **WP(S):** Win probability before the delivery.
    - **WP(Sₒ):** Win probability after simulating that outcome.

    The key safeguard is that the actual next delivery is not used to
    calculate its own pre-delivery pressure score.
    """)

    st.markdown("---")

    # PAR MODEL
    st.markdown("### 3. First-Innings Historical Par Model")

    st.markdown("""
    In the first innings, there is no chase target or required run rate.
    We therefore estimate how many runs a team would historically be
    expected to score from the current innings state.

    The model considers format, legal balls bowled, wickets lost and
    innings length. It is trained chronologically using earlier matches.
    """)

    st.markdown("""
    <div class="formula">
    Par Deficit = Expected Par Score − Actual Score
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    A positive par deficit indicates that the batting team is behind
    its historical scoring expectation at that point. A negative value
    indicates that it is ahead.
    """)

    st.markdown("---")

    # ROLE SPECIFIC
    st.markdown("### 4. Role-Specific Pressure Intelligence")

    left, right = st.columns(2)

    with left:
        st.markdown("""
        <div class="info-card">
            <div class="info-number">BATTER MODEL</div>
            <div class="info-title">Batter Pressure Intelligence (BPI)</div>
            <div class="info-text">
                BPI combines overall match pressure with batting urgency,
                dismissal risk and batting responsibility.

                <br><br>
                <b>Weights:</b><br>
                • HDPI: 35%<br>
                • Batting urgency: 25%<br>
                • Dismissal risk: 20%<br>
                • Responsibility: 20%
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div class="info-card">
            <div class="info-number">BOWLER MODEL</div>
            <div class="info-title">Bowler Pressure Intelligence (BoPI)</div>
            <div class="info-text">
                BoPI combines overall match pressure with defence urgency,
                wicket threat and execution responsibility.

                <br><br>
                <b>Weights:</b><br>
                • HDPI: 35%<br>
                • Defence urgency: 25%<br>
                • Wicket threat: 20%<br>
                • Responsibility: 20%
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # EXPECTED PERFORMANCE
    st.markdown("### 5. Expected Performance & Pressure Advantage")

    st.markdown("""
    A player's raw runs or wickets alone do not explain whether they
    performed well under pressure.

    CLUTCH IQ first estimates expected performance from historical
    match situations. Actual performance is then compared against
    the model's expectation.
    """)

    st.markdown("""
    <div class="formula">
    Batter Residual = Actual Runs − Expected Runs<br><br>
    Bowler Residual = Expected Runs Conceded − Actual Runs Conceded
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    The pressure-performance rate is compared with the normal-performance
    rate. The resulting difference is the player's pressure lift.

    A positive lift indicates that the player performed better relative
    to expectation under pressure than in normal situations.

    We also retain a separate credited-wicket probability residual
    as supporting bowling evidence.
    """)

    st.markdown("---")

    # STATISTICAL RELIABILITY
    st.markdown("### 6. Statistical Reliability & Ranking")

    st.markdown("""
    **Empirical-Bayes shrinkage**

    Extreme estimates from players with limited evidence are pulled
    towards the population average. This reduces the influence of
    unusually small samples.

    **Match-cluster bootstrap**

    Match-level observations are resampled to estimate uncertainty
    in the pressure-performance difference. This provides a confidence
    interval and the proportion of bootstrap estimates above zero.

    **Minimum eligibility requirements**

    Players must satisfy minimum pressure-match, normal-match and
    ball-exposure requirements. Three threshold settings are used to
    examine how rankings respond to stricter evidence requirements.
    """)

    st.markdown("---")

    # VALIDATION
    st.markdown("### 7. Data Leakage Prevention & Validation")

    st.markdown("""
    The expected-performance and win-probability models use chronological
    out-of-sample evaluation. Training matches precede the matches being
    predicted, and match-level overlap between training and evaluation
    folds is prohibited.

    Pressure features are calculated using information available before
    the delivery. Actual delivery outcomes are used to evaluate player
    performance, not to define that delivery's pressure.

    We evaluate the models using metrics such as mean absolute error,
    Brier score, log loss and ROC-AUC, alongside threshold sensitivity
    and ranking stability.
    """)

    st.markdown("---")

    # MODEL REPORT
    report_file = OUT / "WPL_PAR_UPGRADE_REPORT.md"

    if report_file.exists():
        with st.expander("VIEW TECHNICAL MODEL VALIDATION REPORT"):
            st.markdown(report_file.read_text(encoding="utf-8"))

    metrics_file = OUT / "model_metrics.json"

    if metrics_file.exists():
        try:
            metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            with st.expander("VIEW MODEL EVALUATION METRICS"):
                for section, values in metrics.items():
                    st.markdown(f"**{section.replace('_', ' ').title()}**")
                    if isinstance(values, list):
                        st.dataframe(
                            pd.DataFrame(values),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.write(values)
        except Exception:
            st.caption("Model metrics file could not be read.")


# ============================================================
# FOOTER
# ============================================================

st.markdown("""
<div class="footer">
    <b style="color:#D6FF5F;letter-spacing:2px">CLUTCH IQ</b>
    <br><br>
    Contextual Leverage & Intelligence for Cricket Performance
    <br>
    Evidence-driven analysis · Pre-delivery pressure · Out-of-sample evaluation
    <br><br>
    Research and analytics prototype · 2022–2026
</div>
""", unsafe_allow_html=True)
