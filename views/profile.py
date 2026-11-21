import streamlit as st

from fpl import charts
from fpl.data import (MIN_MINUTES, load_data, ordinal, percentiles, player_gameweeks,
                      season_breakdown, team_fixtures)
from fpl.state import persistent_selectbox

gameweek_data, players, teams = load_data()

# ---------------------------------------------------------------------------
# A ?player=<id> link (from the leaderboard, or shared) sets the selection once
# ---------------------------------------------------------------------------
qp = st.query_params.get("player")
if qp and qp != st.session_state.get("_applied_player_param"):
    match = players[players["id"] == int(qp)] if qp.isdigit() else players.iloc[0:0]
    if not match.empty:
        st.session_state["team"] = match.iloc[0]["team"]
        st.session_state["player_id"] = int(match.iloc[0]["id"])
    st.session_state["_applied_player_param"] = qp

# ---------------------------------------------------------------------------
# Team -> player selection
# ---------------------------------------------------------------------------
st.title("Player profile")

c1, c2 = st.columns(2)
with c1:
    team = persistent_selectbox("Team", sorted(players["team"].unique()), "team")

squad = (players[(players["team"] == team) & (players["minutes"] > 0)]
         .sort_values("total_points", ascending=False))
if squad.empty:
    st.info(f"No {team} players have played any minutes yet.")
    st.stop()

labels = {r.id: f"{r.name} · {r.element_type}" for r in squad.itertuples()}
with c2:
    player_id = persistent_selectbox("Player", list(labels), "player_id",
                                     format_func=labels.get)

# Keep the URL in step with the selection, so the page can be bookmarked
st.query_params["player"] = str(player_id)
st.session_state["_applied_player_param"] = str(player_id)

player = players[players["id"] == player_id].iloc[0]
position_pool = players[(players["element_type"] == player["element_type"]) &
                        (players["minutes"] > MIN_MINUTES)]
points_rank = int((position_pool["total_points"] > player["total_points"]).sum()) + 1

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.header(player["name"])
st.caption(f"{player['team']} · {player['element_type']}")

m = st.columns(5)
m[0].metric("Price", f"£{player['price']:.1f}m")
m[1].metric("Total points", int(player["total_points"]))
m[2].metric("Points per £m", f"{player['value_per_m']:.1f}")
m[3].metric("Minutes", f"{int(player['minutes']):,}")
if player["minutes"] > MIN_MINUTES:
    m[4].metric(f"Points rank ({player['element_type']})", ordinal(points_rank))
else:
    m[4].metric(f"Points rank ({player['element_type']})", "—",
                help=f"Ranks only include players with more than {MIN_MINUTES} minutes.")

overview, form, compare, fixtures_tab = st.tabs(
    ["Overview", "Gameweek form", "Compared with position", "Fixtures"])

# ---------------------------------------------------------------------------
# Overview: percentiles + where the points come from
# ---------------------------------------------------------------------------
with overview:
    st.subheader("Percentiles")
    st.caption(f"Ranked against {player['element_type']}s with more than {MIN_MINUTES} minutes.")
    if player["minutes"] <= MIN_MINUTES:
        st.warning(f"{player['name']} has played {int(player['minutes'])} minutes, under the "
                   f"{MIN_MINUTES}-minute cutoff, so these percentiles are based on limited time.")
    st.altair_chart(charts.percentile_donuts(percentiles(players, player_id)))

    st.subheader("Where the points come from")
    breakdown = season_breakdown(gameweek_data, player_id)
    st.altair_chart(charts.breakdown_bar(breakdown), width="stretch", height=190)
    st.caption("Hover a segment for the raw stat and its share of points. "
               "Negative categories sit left of the zero line.")

# ---------------------------------------------------------------------------
# Gameweek form
# ---------------------------------------------------------------------------
FORM_METRICS = {
    "total_points": ("Points", ",.0f"),
    "price": ("Price (£m)", ".1f"),
    "cum_points_per_m": ("Points per £m (season to date)", ".1f"),
    "points_per_m": ("Points per £m (that gameweek)", ".2f"),
    "minutes": ("Minutes", ",.0f"),
    "threat": ("Threat", ",.1f"),
    "ict_index": ("ICT index", ",.1f"),
    "bps": ("BPS", ",.0f"),
}
with form:
    per_gw = player_gameweeks(gameweek_data, player_id)
    choice = st.segmented_control("Metric", list(FORM_METRICS), default="total_points",
                                  format_func=lambda k: FORM_METRICS[k][0], key="form_metric")
    choice = choice or "total_points"
    title, fmt = FORM_METRICS[choice]
    st.altair_chart(charts.gameweek_line(per_gw, choice, title, fmt), width="stretch")
    if (per_gw["fixtures"] > 1).any():
        dgws = ", ".join(str(g) for g in per_gw.loc[per_gw["fixtures"] > 1, "gameweek"])
        st.caption(f"Double gameweeks ({dgws}) are added together.")

# ---------------------------------------------------------------------------
# Compared with position
# ---------------------------------------------------------------------------
HIST_METRICS = {
    "total_points": ("Total points", 10),
    "value_per_m": ("Points per £m", 2),
    "bps": ("BPS", 50),
    "ict_index": ("ICT index", 20),
    "threat": ("Threat", 100),
    "creativity": ("Creativity", 100),
    "minutes": ("Minutes played", 250),
}
with compare:
    hist_metric = st.selectbox("Stat", list(HIST_METRICS),
                               format_func=lambda k: HIST_METRICS[k][0], key="hist_metric")
    title, step = HIST_METRICS[hist_metric]
    pool = players[(players["element_type"] == player["element_type"]) &
                   ((players["minutes"] > MIN_MINUTES) | (players["id"] == player_id))]
    st.altair_chart(charts.position_histogram(pool, player_id, hist_metric, title, step),
                    width="stretch")
    st.caption(f"{len(pool)} {player['element_type']}s with more than {MIN_MINUTES} minutes. "
               f"{player['name']}'s bin is highlighted ({title.lower()}: "
               f"{player[hist_metric]:,.1f}).")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
with fixtures_tab:
    st.subheader(f"{team}: opponent strength by gameweek")
    st.altair_chart(charts.opponent_strength(team_fixtures(gameweek_data, team)),
                    width="stretch")
    st.caption("Green = strength 2–3, red = strength 4–5 (FPL's 1–5 team strength rating).")
