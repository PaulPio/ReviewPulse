#!/usr/bin/env python
"""Import reviews from JSON or CSV into an existing book (real dataset mode).

Expects Alembic migrations applied. Run from repo root::

    python scripts/import_reviews.py --book-id <uuid> --file data/reviews.json

JSON shapes supported:

- ``{ \"reviews\": [ { \"external_key\", \"body\", \"rating\"?, \"review_time\"? } ] }``
- or a bare list of review objects.

``review_time`` may be ISO 8601 string or Unix seconds (UCSD-style).

Dataset citations: see README (UCSD Amazon Review Data, Kaggle samples).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Book, Review


def _parse_time(v: object) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(float(v), tz=UTC)
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_json_reviews(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "reviews" in raw:
        return list(raw["reviews"])
    if isinstance(raw, dict) and "items" in raw:
        # sample_reviews.json shape: flatten
        out: list[dict] = []
        for it in raw["items"]:
            asin = it.get("asin")
            for r in it.get("reviews", []):
                row = dict(r)
                row.setdefault("asin", asin)
                out.append(row)
        return out
    raise SystemExit("JSON must be a list, or dict with 'reviews' / 'items'")


def json_row_to_review_row(row: dict) -> dict:
    ext = row.get("external_key") or row.get("reviewer_id") or row.get("review_id")
    if ext is None:
        raise ValueError("review needs external_key or reviewer_id")
    body = row.get("body") or row.get("reviewText") or row.get("text")
    if not body:
        raise ValueError(f"review {ext!r} missing body/reviewText")
    rd = row.get("review_date") or row.get("review_time") or row.get("unixReviewTime")
    return {
        "external_key": str(ext)[:128],
        "body": str(body),
        "rating": row.get("rating") or row.get("overall"),
        "review_date": _parse_time(rd),
    }


def load_csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        rows = []
        for row in r:
            rows.append(
                {
                    "external_key": row.get("external_key") or row.get("id", ""),
                    "body": row.get("body") or row.get("reviewText") or "",
                    "rating": int(row["rating"]) if row.get("rating") else None,
                    "review_date": _parse_time(row.get("review_date") or row.get("unixReviewTime")),
                }
            )
        return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Import reviews into a book")
    ap.add_argument("--database-url", default="", help="Override DATABASE_URL")
    ap.add_argument("--book-id", required=True, help="Target book UUID")
    ap.add_argument("--file", required=True, help="Path to .json or .csv")
    args = ap.parse_args()

    url = args.database_url or get_settings().database_url
    eng = create_engine(url)
    Session = sessionmaker(bind=eng)
    s = Session()
    try:
        import uuid

        bid = uuid.UUID(args.book_id)
        book = s.get(Book, bid)
        if book is None:
            raise SystemExit(f"Book not found: {bid}")

        path = Path(args.file)
        if path.suffix.lower() == ".csv":
            raw_rows = load_csv_rows(path)
            normalized = [
                {
                    "external_key": r["external_key"],
                    "body": r["body"],
                    "rating": r["rating"],
                    "review_date": r["review_date"],
                }
                for r in raw_rows
                if r["external_key"] and r["body"]
            ]
        else:
            raw_rows = load_json_reviews(path)
            normalized = []
            for row in raw_rows:
                normalized.append(json_row_to_review_row(row))

        n = 0
        for row in normalized:
            existing = s.scalar(
                select(Review).where(
                    Review.book_id == book.id,
                    Review.external_key == row["external_key"],
                )
            )
            if existing:
                existing.body = row["body"]
                if row.get("rating") is not None:
                    existing.rating = row["rating"]
                if row.get("review_date"):
                    existing.review_date = row["review_date"]
                s.add(existing)
            else:
                s.add(
                    Review(
                        book_id=book.id,
                        external_key=row["external_key"],
                        body=row["body"],
                        rating=row.get("rating"),
                        review_date=row.get("review_date"),
                    )
                )
            n += 1
        s.commit()
        print(f"Upserted {n} review rows for book {book.id} ({book.title})")
    finally:
        s.close()


if __name__ == "__main__":
    main()
