import sqlite3
import pandas as pd

DB_PATH = "output/news.db"
TABLE_NAME = "articles"

def init_db():
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