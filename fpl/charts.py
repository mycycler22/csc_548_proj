"""Altair charts for the player profile.

Each function takes data that has already been filtered to one player, team
or position in pandas, so there are no Altair dropdown params here: the
Streamlit widgets do the selecting.
"""
import altair as alt
import numpy as np
import pandas as pd

from .data import BREAKDOWN_CATEGORIES, ordinal

GREEN, AMBER, RED, GREY = "#2ca02c", "#f2b701", "#d62728", "#e6e6e6"
HIGHLIGHT, MUTED = "#e45756", "#c7c7c7"


def percentile_donuts(pct_df: pd.DataFrame, columns: int = 4) -> alt.FacetChart:
    """One donut per stat, filled to the player's percentile within position."""
    df = pct_df.copy()
    df["pct_label"] = (df["pct"] * 100).round().astype(int).map(ordinal)
    df["filled"] = df["pct"]
    df["remaining"] = 1 - df["pct"]
    df = df.melt(id_vars=["stat_label", "value", "pct", "pct_label", "compared_with"],
                 value_vars=["filled", "remaining"], var_name="part", value_name="share")
    df["part_order"] = np.where(df["part"] == "filled", 0, 1)
    df["fill"] = np.select(
        [df["part"] == "remaining", df["pct"] >= 0.67, df["pct"] >= 0.33],
        [GREY, GREEN, AMBER], RED)

    arcs = alt.Chart().mark_arc(innerRadius=42, outerRadius=60).encode(
        theta=alt.Theta("share:Q", stack=True),
        color=alt.Color("fill:N", scale=None),
        order=alt.Order("part_order:Q"),
        tooltip=[
            alt.Tooltip("stat_label:N", title="Stat"),
            alt.Tooltip("value:Q", title="Value", format=",.1~f"),
            alt.Tooltip("pct:Q", title="Percentile", format=".0%"),
            alt.Tooltip("compared_with:Q", title="Players compared"),
        ],
    )
    label = (alt.Chart().transform_filter("datum.part == 'filled'")
             .mark_text(fontSize=18, fontWeight="bold")
             .encode(text="pct_label:N"))
    order = list(pct_df["stat_label"])
    return (
        alt.layer(arcs, label)
        .properties(width=130, height=130)
        .facet(facet=alt.Facet("stat_label:N", title=None, sort=order,
                               header=alt.Header(labelFontSize=12, labelFontWeight="bold")),
               columns=columns, data=df)
        .configure_view(stroke=None)
    )


def gameweek_line(per_gw: pd.DataFrame, field: str, title: str, fmt: str = ",.1~f") -> alt.Chart:
    return (
        alt.Chart(per_gw)
        .mark_line(point=alt.OverlayMarkDef(size=80))
        .encode(
            x=alt.X("gameweek:O", title="Gameweek", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{field}:Q", title=title, scale=alt.Scale(zero=field != "price")),
            tooltip=[
                alt.Tooltip("gameweek:O", title="Gameweek"),
                alt.Tooltip(f"{field}:Q", title=title, format=fmt),
                alt.Tooltip("minutes:Q", title="Minutes"),
                alt.Tooltip("fixtures:Q", title="Fixtures"),
            ],
        )
        .properties(height=300)
    )


def breakdown_bar(breakdown: pd.DataFrame) -> alt.LayerChart:
    """Single horizontal stacked bar of season points by category."""
    df = breakdown.copy()
    df["player"] = "Season"
    bars = alt.Chart(df).mark_bar(height=44).encode(
        x=alt.X("points:Q", title="Total points"),
        y=alt.Y("player:N", title=None, axis=None),
        color=alt.Color("category:N",
                        scale=alt.Scale(domain=BREAKDOWN_CATEGORIES, scheme="tableau10"),
                        title=None, legend=alt.Legend(orient="top", columns=5,
                                                      symbolType="square")),
        order=alt.Order("order:Q"),
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("raw_stat:N", title="Stat"),
            alt.Tooltip("raw_value:Q", title="Raw value"),
            alt.Tooltip("points:Q", title="Points"),
            alt.Tooltip("pct_of_earned:Q", title="% of points earned", format=".1%"),
            alt.Tooltip("pct_of_net:Q", title="% of net total", format=".1%"),
        ],
    )
    zero = alt.Chart().mark_rule(color="black").encode(x=alt.datum(0))
    return (bars + zero).properties(height=60, padding={"bottom": 10})


def position_histogram(pool: pd.DataFrame, player_id: int, field: str,
                       title: str, step: float) -> alt.Chart:
    """Histogram of a stat across the position, with the player's bin highlighted."""
    values = pool[field].astype(float)
    start = np.floor(values.min() / step) * step
    edges = np.arange(start, values.max() + step, step)
    if len(edges) < 2:
        edges = np.array([start, start + step])
    bins = pd.cut(values, edges, right=False, include_lowest=True)
    df = (pd.DataFrame({"bin": bins, "is_player": pool["id"] == player_id})
          .groupby("bin", observed=False)
          .agg(players=("is_player", "size"), has_player=("is_player", "any"))
          .reset_index())
    df["start"] = [b.left for b in df["bin"]]
    df["end"] = [b.right for b in df["bin"]]
    df["group"] = np.where(df["has_player"], "Selected player", "Other players")
    df = df.drop(columns="bin")

    return (
        alt.Chart(df)
        .mark_bar(stroke="white")
        .encode(
            x=alt.X("start:Q", bin="binned", title=title),
            x2="end:Q",
            y=alt.Y("players:Q", title="Number of players"),
            color=alt.Color("group:N", title=None,
                            scale=alt.Scale(domain=["Selected player", "Other players"],
                                            range=[HIGHLIGHT, MUTED])),
            tooltip=[alt.Tooltip("start:Q", title="From", format=",.1~f"),
                     alt.Tooltip("end:Q", title="To", format=",.1~f"),
                     alt.Tooltip("players:Q", title="Players")],
        )
        .properties(height=300)
    )


def opponent_strength(fixtures: pd.DataFrame) -> alt.LayerChart:
    """Opponent strength by gameweek: 2–3 green, 4–5 red."""
    base = alt.Chart(fixtures).encode(
        x=alt.X("gameweek:O", title="Gameweek", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("opponent_strength:Q", title="Opponent strength",
                scale=alt.Scale(domain=[1, 5]),
                axis=alt.Axis(values=[1, 2, 3, 4, 5], format="d")),
    )
    line = base.mark_line(color="#bbbbbb")
    points = base.mark_point(filled=True, size=110, opacity=1).encode(
        color=alt.condition("datum.opponent_strength >= 4", alt.value(RED), alt.value(GREEN)),
        tooltip=[
            alt.Tooltip("gameweek:O", title="Gameweek"),
            alt.Tooltip("opponent_name:N", title="Opponent"),
            alt.Tooltip("venue:N", title="Venue"),
            alt.Tooltip("opponent_strength:Q", title="Opponent strength"),
        ],
    )
    return (line + points).properties(height=280)
