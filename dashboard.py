from pathlib import Path
import pandas as pd
import streamlit as st

CSV_PATH = Path("output/articles_with_sentiment.csv")

st.set_page_config(page_title="News Sentiment Dashboard", layout="wide")
st.title("📰 News Sentiment Dashboard")

if not CSV_PATH.exists():
    st.error(
        "Missing file: output/articles_with_sentiment.csv\n\n"
        "Fix:\n"
        "1) Run locally: python scraper.py --max 20\n"
        "2) Upload/commit output/articles_with_sentiment.csv to your GitHub repo\n"
        "3) Reboot the Streamlit app"
    )
    st.stop()

df = pd.read_csv(CSV_PATH)

# Clean sentiment column (if present)
if "sentiment" in df.columns:
    df["sentiment"] = df["sentiment"].astype(str).str.lower().str.strip()

st.sidebar.header("Filters")
sentiment_options = ["all"]
if "sentiment" in df.columns:
    sentiment_options += sorted([s for s in df["sentiment"].dropna().unique().tolist() if s])

sentiment_choice = st.sidebar.selectbox("Sentiment", sentiment_options)
keyword = st.sidebar.text_input("Keyword (in title)", "")

df_view = df.copy()

if sentiment_choice != "all" and "sentiment" in df_view.columns:
    df_view = df_view[df_view["sentiment"] == sentiment_choice]

title_col = "title" if "title" in df_view.columns else ("headline" if "headline" in df_view.columns else None)
if keyword and title_col:
    df_view = df_view[df_view[title_col].astype(str).str.contains(keyword, case=False, na=False)]

st.subheader("Sentiment counts")
if "sentiment" in df.columns:
    st.write(df["sentiment"].value_counts())
else:
    st.info("No 'sentiment' column found in the CSV.")

st.subheader("Articles")
preferred_cols = [c for c in ["sentiment", "title", "headline", "published", "date", "url"] if c in df_view.columns]
st.dataframe(df_view[preferred_cols] if preferred_cols else df_view, use_container_width=True)

st.download_button(
    "Download filtered CSV",
    data=df_view.to_csv(index=False).encode("utf-8"),
    file_name="filtered_articles.csv",
    mime="text/csv",
)