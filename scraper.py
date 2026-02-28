import os
import re
import time
import json
import argparse
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from dateutil import parser as dateparser

# Sentiment (VADER)
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# SQLite helper
from db_utils import save_to_db

# =============================
# DEFAULT CONFIG
# =============================
BASE_URL = "https://www.bbc.com"
DEFAULT_LISTING_URL = "https://www.bbc.com/news"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0 Safari/537.36"
}

REQUEST_TIMEOUT = 20


# =============================
# HELPERS
# =============================
def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def infer_category(article_url: str) -> str:
    """
    BBC /news/articles/<id> has no category in the URL, so we mark as bbc_news.
    """
    path = urlparse(article_url).path
    if "/news/articles/" in path:
        return "bbc_news"
    parts = [p for p in path.split("/") if p]
    if "news" in parts:
        idx = parts.index("news")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"


def get_article_links(listing_html: str, max_articles: int):
    """
    BBC real stories commonly use: /news/articles/<id>
    Avoid category pages like /news/world/asia
    """
    soup = BeautifulSoup(listing_html, "lxml")

    links = []
    seen = set()

    for a in soup.select("a[href^='/news/articles/']"):
        href = a.get("href")
        if not href:
            continue

        full_url = urljoin(BASE_URL, href)

        if full_url in seen:
            continue

        seen.add(full_url)
        links.append(full_url)

        if len(links) >= max_articles:
            break

    return links


def parse_article(article_url: str):
    html = fetch_html(article_url)
    soup = BeautifulSoup(html, "lxml")

    # Title
    title_el = soup.find("h1")
    title = title_el.get_text(strip=True) if title_el else None

    # Date
    published_at = None
    time_el = soup.find("time")
    if time_el:
        dt = time_el.get("datetime") or time_el.get_text(strip=True)
        try:
            published_at = dateparser.parse(dt).isoformat()
        except Exception:
            published_at = None

    # Author
    author_el = soup.select_one("[data-testid='byline-name']")
    author = author_el.get_text(strip=True) if author_el else None

    # Content
    article_el = soup.find("article")
    if not article_el:
        content = ""
    else:
        paragraphs = article_el.find_all("p")
        content = "\n".join(p.get_text(" ", strip=True) for p in paragraphs)

    content = clean_text(content)

    return {
        "url": article_url,
        "category": infer_category(article_url),
        "title": title,
        "author": author,
        "published_at": published_at,
        "content": content,
        "length": len(content)
    }


# =============================
# SENTIMENT (VADER)
# =============================
def ensure_vader():
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon")


def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    ensure_vader()
    sia = SentimentIntensityAnalyzer()

    def score_text(t: str):
        if not isinstance(t, str) or not t.strip():
            return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0, "sentiment": "neutral"}
        s = sia.polarity_scores(t)
        comp = s["compound"]
        if comp >= 0.05:
            label = "positive"
        elif comp <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        s["sentiment"] = label
        return s

    scores = df["content"].apply(score_text).apply(pd.Series)
    return pd.concat([df, scores], axis=1)


# =============================
# MAIN
# =============================
def main():
    parser = argparse.ArgumentParser(description="BBC News Scraper + Sentiment + SQLite")
    parser.add_argument("--url", default=DEFAULT_LISTING_URL, help="Listing page URL")
    parser.add_argument("--max", type=int, default=20, help="Max articles to scrape")
    parser.add_argument("--sleep", type=float, default=1.0, help="Delay between requests (seconds)")
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)

    run_time = datetime.now().isoformat(timespec="seconds")
    error_log_path = "output/errors.log"

    print(f"Fetching listing: {args.url}")
    listing_html = fetch_html(args.url)

    links = get_article_links(listing_html, args.max)
    print(f"Found {len(links)} article links")

    if not links:
        print("No article links found. BBC markup may have changed.")
        return

    results = []
    errors = []

    for i, url in enumerate(links, start=1):
        try:
            print(f"[{i}/{len(links)}] Scraping: {url}")
            data = parse_article(url)

            # Quality filter
            if data["title"] and data["length"] > 300:
                data["scraped_at"] = run_time
                results.append(data)
            else:
                print("   Skipped (no title or too short)")
        except Exception as e:
            msg = f"{run_time} | {url} | {repr(e)}"
            errors.append(msg)
            print(f"   Error: {e}")

        time.sleep(args.sleep)

    if errors:
        with open(error_log_path, "a", encoding="utf-8") as f:
            for line in errors:
                f.write(line + "\n")
        print(f"\nLogged errors to: {error_log_path}")

    if not results:
        print("\nNo valid articles scraped.")
        return

    df = pd.DataFrame(results).drop_duplicates(subset=["url"], keep="first")

    # ✅ Add sentiment analysis
    df = add_sentiment(df)

    # ✅ Save CSV + JSON
    csv_path = "output/articles_with_sentiment.csv"
    json_path = "output/articles_with_sentiment.json"

    df.to_csv(csv_path, index=False, encoding="utf-8")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {csv_path}")
    print(f"Saved: {json_path}")

    # ✅ Save to SQLite
    save_to_db(df)
    print("\n✅ Saved to SQLite: output/news.db (table: articles)")

    # Preview
    print("\nPreview:")
    print(df[["sentiment", "compound", "title", "published_at", "url"]].head(10))

    print("\nSentiment counts:")
    print(df["sentiment"].value_counts())


if __name__ == "__main__":
    main()