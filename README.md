import sqlite3
import pandas as pd

DB_PATH = "output/news.db"
TABLE_NAME = "articles"


def init_db():
    """Create DB + table if not exists."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        category TEXT,
        title TEXT,
        author TEXT,
        published_at TEXT,
        scraped_at TEXT,
        content TEXT,
        length INTEGER,
        neg REAL,
        neu REAL,
        pos REAL,
        compound REAL,
        sentiment TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_to_db(df: pd.DataFrame):
    """Insert dataframe into SQLite (ignores duplicates by url)."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = df.to_dict(orient="records")

    for r in rows:
        cur.execute(f"""
        INSERT OR IGNORE INTO {TABLE_NAME}
        (url, category, title, author, published_at, scraped_at, content, length,
         neg, neu, pos, compound, sentiment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("url"),
            r.get("category"),
            r.get("title"),
            r.get("author"),
            r.get("published_at"),
            r.get("scraped_at"),
            r.get("content"),
            int(r.get("length") or 0),
            float(r.get("neg") or 0),
            float(r.get("neu") or 0),
            float(r.get("pos") or 0),
            float(r.get("compound") or 0),
            r.get("sentiment")
        ))

    conn.commit()
    conn.close()


def run_query(sql: str) -> pd.DataFrame:
    """Run SQL and return results as DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df
    News Scraper & Sentiment Analysis Dashboard

This project scrapes the latest news articles, analyzes their sentiment, stores results in multiple formats (CSV, JSON, SQLite), and provides a Streamlit dashboard for interactive exploration.

🚀 Features

Scrapes latest news articles (BBC News)

Performs sentiment analysis (positive / negative)

Saves results to:

CSV

JSON

SQLite database

Command-line reporting tool with filters

Interactive Streamlit dashboard

Ready for cloud deployment

📁 Project Structure
news-scraper/
│
├── scraper.py              # Scrapes news & performs sentiment analysis
├── db_utils.py             # SQLite database utilities
├── report.py               # CLI reporting & export tool
├── dashboard.py            # Streamlit web dashboard
├── requirements.txt        # Python dependencies
├── output/
│   ├── articles_with_sentiment.csv
│   ├── articles_with_sentiment.json
│   └── news.db
└── README.md
🛠️ Setup Instructions
1️⃣ Install dependencies
pip install -r requirements.txt
📰 Run the Scraper

Scrape the latest articles and analyze sentiment:

python scraper.py --max 20

This will generate:

output/articles_with_sentiment.csv

output/articles_with_sentiment.json

output/news.db

📊 Run Reports (CLI)

Show latest negative articles:

python report.py --sentiment negative --limit 10

Export filtered results:

python report.py --sentiment positive --limit 50 --out output/positive.csv

Show overall sentiment counts:

python report.py --limit 20 --show-counts
🌐 Run the Dashboard (Local)

Start the Streamlit dashboard:

python -m streamlit run dashboard.py

Then open in browser:

http://localhost:8501
☁️ Deployment (Streamlit Cloud)

Push the project to GitHub

Ensure dashboard.py and requirements.txt are present

Deploy using Streamlit Community Cloud

Set main file path to:

dashboard.py

The app reads data from:

output/articles_with_sentiment.csv
🔄 Updating Data

To refresh data:

Re-run the scraper:

python scraper.py --max 20

Commit and push updated output files to GitHub

The deployed dashboard will reflect the new data

📌 Technologies Used

Python

Requests

BeautifulSoup

Pandas

SQLite

Streamlit

✅ Status

Scraper: ✔ Complete

Sentiment Analysis: ✔ Complete

Database Storage: ✔ Complete

Reporting Tool: ✔ Complete

Dashboard: ✔ Complete

Deployment Ready: ✔