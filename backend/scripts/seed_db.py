"""
Seed the database with demo authors, books, and pre-analysed reviews.

Runs the JSON generator first, then inserts everything directly into the DB
without LLM calls (uses target_* fields from the JSON as analysis ground truth).

Usage (from backend/):
    python -m scripts.seed_db

Idempotent — safe to re-run; existing rows are skipped.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.security import hash_password
from app.db.base import AsyncSessionLocal
from app.models.author import Author
from app.models.book import Book
from app.models.review import Review

# ── Demo accounts ─────────────────────────────────────────────────────────────
_DEMO_PW = "Demo1234"  # noqa: S105 – intentional demo credential

DEMO_AUTHORS = [
    {"display_name": "Maya Chen",     "email": "maya@demo.com"},
    {"display_name": "James Okoye",   "email": "james@demo.com"},
    {"display_name": "Sarah Mitchell","email": "sarah@demo.com"},
]

BOOK_ASSIGNMENTS: dict[str, list[str]] = {
    "Maya Chen":     ["The Last Algorithm", "Neural Dreams", "Code of Silence"],
    "James Okoye":   ["Whispers in the Garden", "The River Between Us", "Midnight Oil"],
    "Sarah Mitchell":["Heart of the Storm", "Second Chances", "The Lighthouse Keeper"],
}

THEME_KEYWORDS: dict[str, list[str]] = {
    "pacing":          ["pacing", "pace", "slow", "fast", "dragged"],
    "characters":      ["character", "protagonist", "hero", "villain"],
    "plot":            ["plot", "story", "narrative", "twist"],
    "writing_style":   ["writing", "prose", "style", "words"],
    "ending":          ["ending", "conclusion", "finale", "climax"],
    "world_building":  ["world", "setting", "atmosphere", "universe"],
    "emotional_impact":["emotional", "moving", "touching", "feel", "heart"],
}


def extract_themes(text: str) -> list[str]:
    lower = text.lower()
    found = [t for t, kws in THEME_KEYWORDS.items() if any(k in lower for k in kws)]
    return found[:4] or ["writing_style"]


def make_summary(text: str) -> str:
    first = text.split(".")[0]
    return (first[:117] + "...") if len(first) > 120 else first


def load_seed_reviews() -> list[dict]:
    data_path = Path(__file__).parent.parent / "data" / "seed_reviews.json"
    if not data_path.exists():
        mod = importlib.import_module("scripts.seed_data")
        mod.main()
    with open(data_path) as f:  # noqa: ASYNC230 – intentional sync I/O before async
        return json.load(f)


async def _upsert_authors(db) -> dict[str, uuid.UUID]:
    author_map: dict[str, uuid.UUID] = {}
    for a in DEMO_AUTHORS:
        existing = await db.execute(select(Author).where(Author.email == a["email"]))
        author = existing.scalar_one_or_none()
        if author:
            author_map[a["display_name"]] = author.id
            print(f"  Author exists:  {a['display_name']}")
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
            print(f"  Created author: {a['display_name']} ({a['email']})")
    await db.flush()
    return author_map


async def _upsert_books(db, author_map: dict[str, uuid.UUID]) -> dict[str, uuid.UUID]:
    book_map: dict[str, uuid.UUID] = {}
    for author_name, titles in BOOK_ASSIGNMENTS.items():
        author_id = author_map[author_name]
        for title in titles:
            existing = await db.execute(
                select(Book).where(Book.title == title, Book.author_id == author_id)
            )
            book = existing.scalar_one_or_none()
            if book:
                book_map[title] = book.id
                print(f"  Book exists:    {title}")
            else:
                new_id = uuid.uuid4()
                db.add(Book(id=new_id, author_id=author_id, title=title))
                book_map[title] = new_id
                print(f"  Created book:   {title}")
    await db.flush()
    return book_map


async def _insert_reviews(
    db, all_reviews: list[dict],
    book_map: dict[str, uuid.UUID],
    author_map: dict[str, uuid.UUID],
) -> tuple[int, int]:
    inserted = skipped = 0
    for r in all_reviews:
        book_id = book_map.get(r["book_title"])
        author_id = author_map.get(r["book_author"])
        if not book_id or not author_id:
            continue

        body = r.get("review_text", "")
        stmt = (
            pg_insert(Review)
            .values(
                id=uuid.uuid4(),
                book_id=book_id,
                author_id=author_id,
                external_id=r["review_id"],
                reviewer_name=r.get("reviewer_name"),
                rating=r.get("rating"),
                title=r.get("review_summary", "")[:512],
                body=body,
                review_date=(
                    datetime.fromisoformat(r["review_date"])
                    if r.get("review_date")
                    else datetime.now(timezone.utc)
                ),
                verified_purchase=r.get("verified_purchase", False),
                source="seed",
                sentiment=r.get("target_sentiment", "mixed"),
                sentiment_confidence=round(random.uniform(0.75, 0.97), 2),
                themes=extract_themes(body),
                is_ai_generated=r.get("target_ai_generated", False),
                ai_generated_confidence=round(
                    random.uniform(0.80, 0.97) if r.get("target_ai_generated") else random.uniform(0.03, 0.20), 2
                ),
                summary=make_summary(body),
                is_actionable=r.get("target_actionable", False),
                actionable_reason=(
                    "Review contains specific feedback the author can act on."
                    if r.get("target_actionable")
                    else None
                ),
                analyzed_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(constraint="uq_reviews_book_external")
        )
        result = await db.execute(stmt)
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


async def seed() -> None:
    all_reviews = load_seed_reviews()

    async with AsyncSessionLocal() as db:
        print("\n--- Authors ---")
        author_map = await _upsert_authors(db)
        await db.commit()

        print("\n--- Books ---")
        book_map = await _upsert_books(db, author_map)
        await db.commit()

        print("\n--- Reviews ---")
        inserted, skipped = await _insert_reviews(db, all_reviews, book_map, author_map)
        await db.commit()

    print(f"\nReviews: {inserted} inserted, {skipped} already existed")
    print("\nDemo accounts (password: Demo1234):")
    for a in DEMO_AUTHORS:
        print(f"  {a['email']}")


if __name__ == "__main__":
    asyncio.run(seed())
