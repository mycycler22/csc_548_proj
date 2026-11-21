## Fantasy Premier League Application

A Streamlit app with two pages:

- **Leaderboards**: top players for any metric, filterable by position and team.
  Click a row to open that player's profile.
- **Player profile**: pick a team, then a player from that team's squad. Shows
  headline stats, percentile donuts, a points breakdown, gameweek form, a
  position histogram and the team's opponent strength.

## Setup

```bash
pip install -r requirements.txt
```

Put your data in the same layout as the notebook uses:

```
fpl_app/
└── data/2025-2026/
    ├── cleaned_players.csv
    ├── player_idlist.csv
    ├── teams.csv
    └── gameweeks/
        ├── gw1.csv
        ├── …
        └── gw38.csv
```

If your data lives somewhere else, change `DATA_DIR` at the top of `fpl/data.py`.
Any number of gameweek files works, so a season in progress is fine.

## Run

```bash
streamlit run app.py
```

## Layout

| File | What it does |
|---|---|
| `app.py` | Page setup and navigation |
| `views/leaderboard.py` | Leaderboard page |
| `views/profile.py` | Player profile page |
| `fpl/data.py` | Loading, joins, points breakdown, percentiles (pandas) |
| `fpl/charts.py` | Altair charts (each takes pre-filtered data) |
| `fpl/state.py` | Team/player selection that persists across pages |

Settings such as the minutes cutoff (`MIN_MINUTES`), leaderboard metrics and
percentile stats are constants at the top of `fpl/data.py`.

Profiles can be linked directly: `/profile?player=<player id>`.
