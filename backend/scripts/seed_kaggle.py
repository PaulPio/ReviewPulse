"""
Seed the database with real Amazon book reviews from Kaggle.

Downloads the 'mohamedbakhet/amazon-books-reviews' dataset via kagglehub,
picks the 9 most-reviewed books, assigns them to 3 demo authors (3 books each),
and inserts up to 50 real reviews per book with analysis derived from ratings.

Usage (from backend/):
    python -m scripts.seed_kaggle

Requirements:
    pip install kagglehub pandas

Kaggle credentials: set KAGGLE_USERNAME + KAGGLE_KEY env vars,
or place ~/.kaggle/kaggle.json  (get it from kaggle.com > Account > API).

Idempotent — safe to re-run; existing rows are skipped.
"""

from __future__ import annotations

import asyncio
import ast
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import kagglehub
    import pandas as pd
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install kagglehub pandas")
    sys.exit(1)

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.security import hash_password
from app.db.base import AsyncSessionLocal
from app.models.author import Author
from app.models.book import Book
from app.models.review import Review

# ── Config ────────────────────────────────────────────────────────────────────
REVIEWS_PER_BOOK = 50
TOTAL_BOOKS = 9

_DEMO_PW = "Demo1234"  # noqa: S105

DEMO_AUTHORS = [
    {"display_name": "Maya Chen",      "email": "maya@demo.com"},
    {"display_name": "James Okoye",    "email": "james@demo.com"},
    {"display_name": "Sarah Mitchell", "email": "sarah@demo.com"},
]

THEME_KEYWORDS: dict[str, list[str]] = {
    "pacing":           ["pacing", "pace", "slow", "fast", "dragged", "rushed"],
    "characters":       ["character", "protagonist", "hero", "villain", "cast"],
    "plot":             ["plot", "story", "narrative", "twist", "storyline"],
    "writing_style":    ["writing", "prose", "style", "author's voice", "descriptive"],
    "ending":           ["ending", "conclusion", "finale", "climax", "resolution"],
    "world_building":   ["world", "setting", "atmosphere", "universe", "immersive"],
    "emotional_impact": ["emotional", "moving", "touching", "feel", "heart", "cry"],
    "dialogue":         ["dialogue", "conversation", "banter", "voice"],
}

ACTIONABLE_KEYWORDS = [
    "typo", "typos", "error", "errors", "formatting", "kindle",
    "chapter", "fix", "wrong", "should have", "could have", "wish",
    "inconsistency", "continuity", "missing", "confusing", "confused",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_themes(text: str) -> list[str]:
    lower = text.lower()
    found = [t for t, kws in THEME_KEYWORDS.items() if any(k in lower for k in kws)]
    return found[:4] or ["writing_style"]


def rating_to_sentiment(score: float) -> str:
    if score >= 4.0:
        return "positive"
    if score >= 3.0:
        return "mixed"
    return "negative"


def make_summary(text: str) -> str:
    first = text.split(".")[0].strip()
    return (first[:117] + "...") if len(first) > 120 else first


def safe_str(val, default: str = "") -> str:
    if pd.isna(val):
        return default
    return str(val).strip()


# ── Data loading ──────────────────────────────────────────────────────────────

def load_kaggle_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    print("Downloading Kaggle dataset (cached after first download)...")
    path = kagglehub.dataset_download("mohamedbakhet/amazon-books-reviews")
    dataset_path = Path(path)
    print(f"Dataset path: {dataset_path}")

    books_csv = dataset_path / "books_data.csv"
    ratings_csv = dataset_path / "Books_rating.csv"

    if not books_csv.exists() or not ratings_csv.exists():
        files = list(dataset_path.glob("*.csv"))
        raise FileNotFoundError(
            f"Expected books_data.csv and Books_rating.csv in {dataset_path}. "
            f"Found: {[f.name for f in files]}"
        )

    books_df = pd.read_csv(books_csv, on_bad_lines="skip")
    ratings_df = pd.read_csv(ratings_csv, on_bad_lines="skip")

    print(f"Loaded {len(books_df):,} book records and {len(ratings_df):,} ratings")
    return books_df, ratings_df


def pick_top_books(
    books_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    n: int = TOTAL_BOOKS,
) -> list[dict]:
    """Return the n most-reviewed books that have real text reviews."""
    # Drop rows without review text or title
    ratings_clean = ratings_df.dropna(subset=["Title", "review/text"])
    ratings_clean = ratings_clean[ratings_clean["review/text"].str.len() > 30]

    review_counts = ratings_clean.groupby("Title").size().reset_index(name="review_count")

    # Merge with book metadata
    merged = books_df.merge(review_counts, on="Title", how="inner")
    merged = merged.dropna(subset=["Title"])
    merged = merged[merged["review_count"] >= REVIEWS_PER_BOOK]
    merged = merged.sort_values("review_count", ascending=False)

    seen: set[str] = set()
    result: list[dict] = []

    for _, row in merged.iterrows():
        title = safe_str(row["Title"])
        if not title or title in seen:
            continue
        seen.add(title)

        # Parse authors field (stored as Python repr string, e.g. "['Author Name']")
        raw_authors = safe_str(row.get("authors", ""))
        try:
            authors_list: list[str] = ast.literal_eval(raw_authors) if raw_authors else []
        except Exception:
            authors_list = []

        # Parse published date
        raw_date = safe_str(row.get("publishedDate", ""))
        published_at: datetime | None = None
        if raw_date:
            for fmt in ("%Y-%m-%d", "%Y"):
                try:
                    published_at = datetime.strptime(raw_date[:10], fmt).replace(
                        tzinfo=timezone.utc
                    )
                    break
                except ValueError:
                    pass

        result.append({
            "title": title,
            "description": safe_str(row.get("description", ""))[:2000] or None,
            "cover_url": safe_str(row.get("image", "")) or None,
            "published_at": published_at,
            "original_authors": authors_list,
            "review_count": int(row["review_count"]),
        })

        if len(result) >= n:
            break

    if not result:
        raise RuntimeError(
            f"Could not find {n} books with {REVIEWS_PER_BOOK}+ reviews. "
            "Try lowering REVIEWS_PER_BOOK."
        )

    return result


# ── DB operations ─────────────────────────────────────────────────────────────

async def _upsert_authors(db) -> dict[str, uuid.UUID]:
    author_map: dict[str, uuid.UUID] = {}
    for a in DEMO_AUTHORS:
        row = await db.execute(select(Author).where(Author.email == a["email"]))
        author = row.scalar_one_or_none()
        if author:
            author_map[a["display_name"]] = author.id
            print(f"  exists : {a['display_name']}")
        else:
            new_id = uuid.uuid4()
            db.add(Author(
                id=new_id,
                email=a["email"],
                display_name=a["display_name"],
                hashed_password=hash_password(_DEMO_PW),
                last_login_at=datetime.now(timezone.utc),
            ))
            author_map[a["display_name"]] = new_id
            print(f"  created: {a['display_name']} ({a['email']})")
    await db.flush()
    return author_map


async def _upsert_books(
    db,
    books_data: list[dict],
    author_map: dict[str, uuid.UUID],
) -> dict[str, uuid.UUID]:
    book_map: dict[str, uuid.UUID] = {}
    author_names = list(author_map.keys())

    for i, book in enumerate(books_data):
        author_name = author_names[i % len(author_names)]
        author_id = author_map[author_name]
        title = book["title"]

        row = await db.execute(
            select(Book).where(Book.title == title, Book.author_id == author_id)
        )
        existing = row.scalar_one_or_none()

        if existing:
            book_map[title] = existing.id
            print(f"  exists : {title}")
        else:
            new_id = uuid.uuid4()
            db.add(Book(
                id=new_id,
                author_id=author_id,
                title=title,
                description=book.get("description"),
                cover_url=book.get("cover_url"),
                published_at=book.get("published_at"),
            ))
            book_map[title] = new_id
            print(f"  created: {title} → {author_name}")

        await db.flush()

    return book_map


async def _insert_reviews(
    db,
    books_data: list[dict],
    book_map: dict[str, uuid.UUID],
    author_map: dict[str, uuid.UUID],
    ratings_df: pd.DataFrame,
) -> tuple[int, int]:
    inserted = skipped = 0
    author_names = list(author_map.keys())

    # Pre-filter ratings to only real text reviews
    ratings_clean = ratings_df.dropna(subset=["Title", "review/text"]).copy()
    ratings_clean = ratings_clean[ratings_clean["review/text"].str.len() > 30]

    for i, book in enumerate(books_data):
        title = book["title"]
        book_id = book_map.get(title)
        if not book_id:
            continue

        author_name = author_names[i % len(author_names)]
        author_id = author_map[author_name]

        book_reviews = ratings_clean[ratings_clean["Title"] == title].head(REVIEWS_PER_BOOK)
        book_inserted = 0

        for _, row in book_reviews.iterrows():
            body = safe_str(row.get("review/text", ""))
            if not body:
                continue

            try:
                score = float(row.get("review/score") or 3)
            except (ValueError, TypeError):
                score = 3.0

            review_summary = safe_str(row.get("review/summary", ""))
            reviewer = safe_str(row.get("profileName", "")) or "Anonymous"
            user_id = safe_str(row.get("User_id", ""))

            # Unix timestamp → datetime
            try:
                ts = float(row.get("review/time") or 0)
                review_date = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
            except (ValueError, TypeError, OSError):
                review_date = datetime.now(timezone.utc)

            sentiment = rating_to_sentiment(score)
            is_actionable = score <= 3.0 and any(k in body.lower() for k in ACTIONABLE_KEYWORDS)

            # Stable external ID: user + title prefix (idempotent)
            ext_id = f"kg_{user_id[:40]}_{title[:30]}" if user_id else f"kg_{uuid.uuid4()}"

            stmt = (
                pg_insert(Review)
                .values(
                    id=uuid.uuid4(),
                    book_id=book_id,
                    author_id=author_id,
                    external_id=ext_id,
                    reviewer_name=reviewer[:255],
                    rating=int(score),
                    title=review_summary[:512] if review_summary else None,
                    body=body,
                    review_date=review_date,
                    verified_purchase=False,
                    source="kaggle",
                    sentiment=sentiment,
                    sentiment_confidence=round(random.uniform(0.78, 0.97), 2),
                    themes=extract_themes(body),
                    is_ai_generated=False,
                    ai_generated_confidence=round(random.uniform(0.03, 0.15), 2),
                    summary=make_summary(body),
                    is_actionable=is_actionable,
                    actionable_reason=(
                        "Review contains specific feedback the author can act on."
                        if is_actionable else None
                    ),
                    analyzed_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_nothing(constraint="uq_reviews_book_external")
            )
            result = await db.execute(stmt)
            if result.rowcount:
                inserted += 1
                book_inserted += 1
            else:
                skipped += 1

        print(f"  {title[:60]}: {book_inserted} reviews inserted")

    return inserted, skipped


# ── Entry point ───────────────────────────────────────────────────────────────

async def seed() -> None:
    books_df, ratings_df = load_kaggle_data()

    print(f"\nSelecting top {TOTAL_BOOKS} books with {REVIEWS_PER_BOOK}+ reviews...")
    books_data = pick_top_books(books_df, ratings_df)
    print(f"Selected {len(books_data)} books:")
    for b in books_data:
        print(f"  {b['title'][:60]} ({b['review_count']} reviews available)")

    async with AsyncSessionLocal() as db:
        print("\n--- Authors ---")
        author_map = await _upsert_authors(db)
        await db.commit()

        print("\n--- Books ---")
        book_map = await _upsert_books(db, books_data, author_map)
        await db.commit()

        print("\n--- Reviews ---")
        inserted, skipped = await _insert_reviews(db, books_data, book_map, author_map, ratings_df)
        await db.commit()

    print(f"\nDone. Reviews inserted: {inserted}, skipped (already existed): {skipped}")
    print("\nDemo accounts (password: Demo1234):")
    for a in DEMO_AUTHORS:
        print(f"  {a['email']}")


if __name__ == "__main__":
    asyncio.run(seed())
