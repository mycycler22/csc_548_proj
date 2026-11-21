"""Selections that persist across pages.

Streamlit forgets a widget's value when you leave the page it's on, so the
real selection lives in its own session-state key ("team", "player_id") and
each widget is re-seeded from it every time the page runs.
"""
import streamlit as st

PROFILE_PAGE = "views/profile.py"


def _sync(widget_key: str, store_key: str) -> None:
    st.session_state[store_key] = st.session_state[widget_key]


def persistent_selectbox(label, options, store_key, format_func=str, **kwargs):
    """A selectbox whose value survives page switches.

    If the stored value isn't one of the options (e.g. the team changed),
    it falls back to the first option.
    """
    options = list(options)
    if st.session_state.get(store_key) not in options:
        st.session_state[store_key] = options[0]
    widget_key = f"_{store_key}_widget"
    st.session_state[widget_key] = st.session_state[store_key]
    st.selectbox(label, options, key=widget_key, format_func=format_func,
                 on_change=_sync, args=(widget_key, store_key), **kwargs)
    return st.session_state[store_key]


def open_profile(team: str, player_id: int) -> None:
    """Select a player and go to the profile page."""
    st.session_state["team"] = team
    st.session_state["player_id"] = int(player_id)
    st.switch_page(PROFILE_PAGE, query_params={"player": str(int(player_id))})
