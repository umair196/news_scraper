import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "output/news.db"
TABLE = "articles"

st.set_page_config(page_title="News Sentiment Dashboard", layout="wide")
st.title("📰 News Sentiment Dashboard")

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(f"SELECT * FROM {TABLE}", conn)
conn.close()

if df.empty:
    st.warning("No data found in the database.")
    st.stop()

# Filters
sentiments = ["All"] + sorted(df["sentiment"].dropna().unique().tolist())
choice = st.selectbox("Sentiment filter", sentiments)

if choice != "All":
    df_view = df[df["sentiment"] == choice].copy()
else:
    df_view = df.copy()

st.subheader("Sentiment counts")
st.write(df["sentiment"].value_counts())

st.subheader("Articles")
# show best-guess columns
preferred = [c for c in ["sentiment", "title", "headline", "published", "date", "url", "link"] if c in df_view.columns]
st.dataframe(df_view[preferred] if preferred else df_view, use_container_width=True)