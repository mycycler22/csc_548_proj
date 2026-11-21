import streamlit as st

st.set_page_config(page_title="FPL Player Explorer", page_icon="⚽", layout="wide")

pages = [
    st.Page("views/leaderboard.py", title="Leaderboards", icon=":material/leaderboard:", default=True),
    st.Page("views/profile.py", title="Player profile", icon=":material/person:"),
]
st.navigation(pages, position="top").run()
