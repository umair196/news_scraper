import argparse
import sqlite3
from pathlib import Path

import pandas as pd


def connect(db_path: str) -> sqlite3.Connection:
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"Database not found: {db_file.resolve()}")
    return sqlite3.connect(str(db_file))


def get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table});")
    rows = cur.fetchall()
    if not rows:
        raise ValueError(f"Table '{table}' not found (or has no columns).")
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return [r[1] for r in rows]


def build_query(table: str, sentiment: str | None, limit: int, order_by: str | None) -> tuple[str, list]:
    query = f"SELECT * FROM {table}"
    params: list = []

    if sentiment:
        query += " WHERE sentiment = ?"
        params.append(sentiment)

    if order_by:
        # order_by is controlled by us (validated against columns), so safe to interpolate
        query += f" ORDER BY {order_by} DESC"
    else:
        # fallback if no obvious date/id column exists
        query += " ORDER BY rowid DESC"

    query += " LIMIT ?"
    params.append(limit)

    return query, params


def choose_display_columns(all_cols: list[str]) -> list[str]:
    """
    Prefer common columns if they exist; otherwise show first few columns.
    """
    preferred = ["sentiment", "title", "headline", "summary", "published", "date", "url", "link"]
    cols = [c for c in preferred if c in all_cols]

    # If no common cols match, show up to first 6 columns
    if not cols:
        cols = all_cols[:6]

    # Make sure URL-ish column is included if present
    for c in ["url", "link"]:
        if c in all_cols and c not in cols:
            cols.append(c)

    return cols


def pick_order_by_column(all_cols: list[str]) -> str | None:
    """
    Try to order by a sensible "latest first" column if available.
    """
    for c in ["published", "published_at", "date", "created_at", "timestamp", "id"]:
        if c in all_cols:
            return c
    return None


def sentiment_counts(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(
        f"SELECT sentiment, COUNT(*) AS count FROM {table} GROUP BY sentiment ORDER BY count DESC;",
        conn,
    )


def main():
    parser = argparse.ArgumentParser(description="News DB Report Tool")
    parser.add_argument("--db", default="output/news.db", help="Path to SQLite DB (default: output/news.db)")
    parser.add_argument("--table", default="articles", help="Table name (default: articles)")
    parser.add_argument("--sentiment", help="Filter by sentiment (e.g., positive/negative)")
    parser.add_argument("--limit", type=int, default=10, help="Number of rows to show (default: 10)")
    parser.add_argument("--out", help="Optional output file path (.csv or .json) to export results")
    parser.add_argument("--show-counts", action="store_true", help="Show overall sentiment counts in the table")
    args = parser.parse_args()

    conn = connect(args.db)

    try:
        cols = get_table_columns(conn, args.table)
        order_by = pick_order_by_column(cols)

        query, params = build_query(args.table, args.sentiment, args.limit, order_by)
        df = pd.read_sql_query(query, conn, params=params)

        if df.empty:
            print("No articles found for the given filters.")
            return

        display_cols = choose_display_columns(list(df.columns))

        print("\nResults:\n")
        # Print without index for cleaner output
        print(df[display_cols].to_string(index=False))

        if args.show_counts:
            print("\nOverall sentiment counts (entire table):\n")
            counts_df = sentiment_counts(conn, args.table)
            print(counts_df.to_string(index=False))

        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if out_path.suffix.lower() == ".csv":
                df.to_csv(out_path, index=False)
            elif out_path.suffix.lower() == ".json":
                df.to_json(out_path, orient="records", force_ascii=False, indent=2)
            else:
                raise ValueError("Unsupported --out format. Use .csv or .json")

            print(f"\nSaved export: {out_path.resolve()}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()