"""Data loading and preparation for the FPL app.

Everything here is plain pandas, so the charts only ever receive the rows
they need (one player, one team, one position) instead of the full dataset.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "2025-2026"

MIN_MINUTES = 450          # minimum season minutes for leaderboards and percentiles
POSITIONS = ["GK", "DEF", "MID", "FWD"]

LEADERBOARD_METRICS = {
    "total_points": "Total points",
    "value_per_m": "Points per £m",
    "goals_scored": "Goals",
    "assists": "Assists",
    "clean_sheets": "Clean sheets",
    "bonus": "Bonus points",
    "bps": "BPS",
    "ict_index": "ICT index",
    "threat": "Threat",
    "creativity": "Creativity",
    "influence": "Influence",
    "minutes": "Minutes played",
}

PERCENTILE_STATS = {
    "total_points": "Total points",
    "minutes": "Minutes played",
    "value_per_m": "Points per £m",
    "ict_index": "ICT index",
    "bps": "BPS",
    "threat": "Threat",
    "creativity": "Creativity",
}

BREAKDOWN_CATEGORIES = [
    "Appearance", "Goals", "Assists", "Clean sheets", "Saves",
    "Defensive contribution", "Bonus", "Goals conceded", "Cards", "Other",
]

RAW_STAT_NAMES = {
    "Appearance": "Minutes played",
    "Goals": "Goals scored",
    "Assists": "Assists",
    "Clean sheets": "Clean sheets",
    "Saves": "Saves (incl. penalties)",
    "Defensive contribution": "Defensive actions",
    "Bonus": "BPS score",
    "Goals conceded": "Goals conceded",
    "Cards": "Cards (yellow + red)",
    "Other": "Own goals + penalties missed",
}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading FPL data…")
def load_data(data_dir: str = str(DATA_DIR)):
    """Return (gameweek_data, players, teams)."""
    data_dir = Path(data_dir)

    # Gameweek files: gw1.csv … gw38.csv (any number that exist)
    gw_files = sorted((data_dir / "gameweeks").glob("gw*.csv"),
                      key=lambda p: int(p.stem[2:]))
    if not gw_files:
        raise FileNotFoundError(f"No gameweek files found in {data_dir / 'gameweeks'}")
    frames = []
    for path in gw_files:
        df = pd.read_csv(path)
        df["gameweek"] = int(path.stem[2:])
        frames.append(df)
    gameweek_data = pd.concat(frames, ignore_index=True)

    # Opponent name and strength (opponent_team is the opponent's id in teams.csv)
    teams = pd.read_csv(data_dir / "teams.csv")
    opponents = teams[["id", "name", "short_name", "strength"]].rename(columns={
        "id": "opponent_team", "name": "opponent_name",
        "short_name": "opponent", "strength": "opponent_strength",
    })
    gameweek_data = gameweek_data.merge(opponents, on="opponent_team", how="left")
    gameweek_data["price"] = gameweek_data["value"] / 10

    # Season totals, with the player id from player_idlist (joined on full name)
    players = pd.read_csv(data_dir / "cleaned_players.csv")
    players["name"] = players["first_name"] + " " + players["second_name"]
    ids = pd.read_csv(data_dir / "player_idlist.csv")
    ids["name"] = ids["first_name"] + " " + ids["second_name"]
    ids = ids.drop_duplicates("name")[["id", "name"]]
    players = players.merge(ids, on="name", how="left")
    players["price"] = players["now_cost"] / 10

    # Current team = the team in the player's most recent gameweek row
    latest = (gameweek_data.sort_values(["gameweek", "kickoff_time"])
              .groupby("element").tail(1)[["element", "team"]]
              .rename(columns={"element": "id"}))
    players = players.merge(latest, on="id", how="left")

    # Players with no id or no gameweek rows can't have a profile
    players = players.dropna(subset=["id", "team"]).copy()
    players["id"] = players["id"].astype(int)

    return gameweek_data, players, teams


# --------------------------------------------------------------------------
# Leaderboard
# --------------------------------------------------------------------------
def leaderboard(players: pd.DataFrame, metric: str, position: str = "All",
                team: str = "All teams", top_n: int = 10) -> pd.DataFrame:
    df = players[players["minutes"] > MIN_MINUTES]
    if position != "All":
        df = df[df["element_type"] == position]
    if team != "All teams":
        df = df[df["team"] == team]
    df = df.sort_values(metric, ascending=False).head(top_n).copy()
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


# --------------------------------------------------------------------------
# Player profile helpers
# --------------------------------------------------------------------------
def player_gameweeks(gameweek_data: pd.DataFrame, player_id: int) -> pd.DataFrame:
    """One row per gameweek for a player (double gameweeks are summed)."""
    rows = gameweek_data[gameweek_data["element"] == player_id]
    sums = ["total_points", "minutes", "goals_scored", "assists", "bps", "bonus",
            "threat", "creativity", "influence", "ict_index", "expected_goals",
            "expected_assists", "defensive_contribution"]
    sums = [c for c in sums if c in rows.columns]
    per_gw = (rows.sort_values(["gameweek", "kickoff_time"])
              .groupby("gameweek")
              .agg({**{c: "sum" for c in sums}, "price": "last", "fixture": "count"})
              .rename(columns={"fixture": "fixtures"})
              .reset_index())
    per_gw["points_per_m"] = per_gw["total_points"] / per_gw["price"]
    per_gw["cum_points_per_m"] = per_gw["total_points"].cumsum() / per_gw["price"]
    return per_gw


def points_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Points per category for each gameweek row, using FPL 2025/26 scoring."""
    pos = df["position"]
    mins = df["minutes"]
    out = pd.DataFrame(index=df.index)
    out["Appearance"] = np.select([mins >= 60, mins > 0], [2, 1], 0)
    out["Goals"] = df["goals_scored"] * pos.map({"GK": 10, "DEF": 6, "MID": 5, "FWD": 4})
    out["Assists"] = df["assists"] * 3
    out["Clean sheets"] = df["clean_sheets"] * pos.map({"GK": 4, "DEF": 4, "MID": 1, "FWD": 0})
    out["Saves"] = (df["saves"] // 3) + df["penalties_saved"] * 5
    dc_threshold = pos.map({"GK": np.inf, "DEF": 10, "MID": 12, "FWD": 12})
    out["Defensive contribution"] = np.where(df["defensive_contribution"] >= dc_threshold, 2, 0)
    out["Bonus"] = df["bonus"]
    out["Goals conceded"] = np.where(pos.isin(["GK", "DEF"]), -(df["goals_conceded"] // 2), 0)
    out["Cards"] = -df["yellow_cards"] - 3 * df["red_cards"]
    out["Other"] = -2 * df["own_goals"] - 2 * df["penalties_missed"]
    # Anything the rules above miss goes into Other, so totals always match total_points
    out["Other"] += df["total_points"] - out.sum(axis=1)
    return out


def raw_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["Appearance"] = df["minutes"]
    out["Goals"] = df["goals_scored"]
    out["Assists"] = df["assists"]
    out["Clean sheets"] = df["clean_sheets"]
    out["Saves"] = df["saves"] + df["penalties_saved"]
    out["Defensive contribution"] = df["defensive_contribution"]
    out["Bonus"] = df["bps"]
    out["Goals conceded"] = df["goals_conceded"]
    out["Cards"] = df["yellow_cards"] + df["red_cards"]
    out["Other"] = df["own_goals"] + df["penalties_missed"]
    return out


def season_breakdown(gameweek_data: pd.DataFrame, player_id: int) -> pd.DataFrame:
    """One row per category: season points, raw stat and % of points."""
    rows = gameweek_data[gameweek_data["element"] == player_id]
    pts = points_breakdown(rows).sum()
    raw = raw_breakdown(rows).sum()
    df = pd.DataFrame({
        "category": BREAKDOWN_CATEGORIES,
        "points": [pts[c] for c in BREAKDOWN_CATEGORIES],
        "raw_value": [raw[c] for c in BREAKDOWN_CATEGORIES],
    })
    df["raw_stat"] = df["category"].map(RAW_STAT_NAMES)
    df["order"] = range(len(df))
    earned = df["points"].clip(lower=0).sum()
    net = df["points"].sum()
    df["pct_of_earned"] = df["points"] / earned if earned > 0 else np.nan
    df["pct_of_net"] = df["points"] / net if net != 0 else np.nan
    return df


def percentiles(players: pd.DataFrame, player_id: int) -> pd.DataFrame:
    """Percentile (0–1) for each stat, ranked within the player's position.

    The pool is regular players (> MIN_MINUTES) plus the selected player, so a
    player below the cutoff still gets a result.
    """
    player = players.loc[players["id"] == player_id].iloc[0]
    pool = players[(players["element_type"] == player["element_type"]) &
                   ((players["minutes"] > MIN_MINUTES) | (players["id"] == player_id))]
    n = len(pool)
    rows = []
    for stat, label in PERCENTILE_STATS.items():
        rank = pool[stat].rank(method="min")           # same as Vega's percent_rank
        pct = (rank[pool["id"] == player_id].iloc[0] - 1) / (n - 1) if n > 1 else 1.0
        rows.append({"stat": stat, "stat_label": label,
                     "value": player[stat], "pct": pct, "compared_with": n})
    return pd.DataFrame(rows)


def team_fixtures(gameweek_data: pd.DataFrame, team: str) -> pd.DataFrame:
    rows = gameweek_data[gameweek_data["team"] == team]
    return (rows[["gameweek", "fixture", "kickoff_time", "opponent", "opponent_name",
                  "opponent_strength", "was_home"]]
            .drop_duplicates("fixture")
            .sort_values(["gameweek", "kickoff_time"])
            .assign(venue=lambda d: np.where(d["was_home"], "H", "A")))


def ordinal(n: int) -> str:
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
