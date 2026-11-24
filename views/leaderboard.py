import streamlit as st

from fpl.data import LEADERBOARD_METRICS, MIN_MINUTES, POSITIONS, leaderboard, load_data
from fpl.state import open_profile

gameweek_data, players, teams = load_data()

## Header/additional information

st.title("Leaderboards")
st.caption(f"Players with more than {MIN_MINUTES} minutes this season. "
           "Click a row to open that player's profile.")

c1, c2, c3, c4 = st.columns([2, 1.2, 1.6, 1])
metric = c1.selectbox("Metric", list(LEADERBOARD_METRICS),
                      format_func=LEADERBOARD_METRICS.get, key="lb_metric")
position = c2.selectbox("Position", ["All"] + POSITIONS, key="lb_position")
team = c3.selectbox("Team", ["All teams"] + sorted(players["team"].unique()), key="lb_team")
top_n = c4.number_input("Show top", min_value=5, max_value=100, value=10, step=5, key="lb_top_n")

board = leaderboard(players, metric, position, team, int(top_n))
metric_label = LEADERBOARD_METRICS[metric]

if board.empty:
    st.info("No players match these filters.")
    st.stop()

columns = ["rank", "name", "team", "element_type", "price", "total_points"]
if metric not in columns:                         # no second Points column for "Total points"
    columns.append(metric)
table = board[columns].copy()
value_col = metric


st.session_state.setdefault("lb_table_version", 0)
event = st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    on_select="rerun",
    selection_mode="single-row",
    key=f"lb_table_{st.session_state['lb_table_version']}",
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "name": st.column_config.TextColumn("Player"),
        "team": st.column_config.TextColumn("Team"),
        "element_type": st.column_config.TextColumn("Pos", width="small"),
        "price": st.column_config.NumberColumn("Price", format="£%.1fm"),
        "total_points": st.column_config.NumberColumn("Points"),
        value_col: st.column_config.ProgressColumn(
            metric_label,
            format="%.1f" if board[metric].dtype.kind == "f" else "%d",
            min_value=0,
            max_value=float(board[metric].max()),
        ),
    },
)

if event.selection.rows:
    row = board.iloc[event.selection.rows[0]]
    st.session_state["lb_table_version"] += 1
    open_profile(row["team"], row["id"])
