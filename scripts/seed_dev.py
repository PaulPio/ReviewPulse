#!/usr/bin/env python
"""Seed a dev author and sample books.

Requires migrations applied: `cd backend && alembic upgrade head`

Run from repo root: python scripts/seed_dev.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Author, Book


def main() -> None:
    settings = get_settings()
    eng = create_engine(settings.database_url)
    Session = sessionmaker(bind=eng)
    s = Session()
    a = Author(display_name="Seeded author")
    s.add(a)
    s.commit()
    s.refresh(a)
    for title, asin in [
        ("Demo title A", "DEMOASIN01"),
        ("Demo title B", "DEMOASIN02"),
    ]:
        s.add(Book(author_id=a.id, title=title, asin=asin))
    s.commit()
    print(f"Author id (use as X-Dev-Author-Id): {a.id}")


if __name__ == "__main__":
    main()
