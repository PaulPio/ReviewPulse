"""
Seed script: Generate synthetic review data for ReviewPulse demo.

Creates 3 authors, 9 books, and ~200 reviews with realistic distribution.
Run: python -m scripts.seed_data
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Seed data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

AUTHORS = [
    {"name": "Maya Chen", "email": "maya@example.com"},
    {"name": "James Okoye", "email": "james@example.com"},
    {"name": "Sarah Mitchell", "email": "sarah@example.com"},
]

BOOKS = [
    # Maya Chen's books
    {"title": "The Last Algorithm", "author": "Maya Chen", "genre": "sci-fi thriller"},
    {"title": "Neural Dreams", "author": "Maya Chen", "genre": "sci-fi"},
    {"title": "Code of Silence", "author": "Maya Chen", "genre": "techno-thriller"},
    # James Okoye's books
    {"title": "Whispers in the Garden", "author": "James Okoye", "genre": "literary fiction"},
    {"title": "The River Between Us", "author": "James Okoye", "genre": "historical fiction"},
    {"title": "Midnight Oil", "author": "James Okoye", "genre": "mystery"},
    # Sarah Mitchell's books
    {"title": "Heart of the Storm", "author": "Sarah Mitchell", "genre": "romance"},
    {"title": "Second Chances", "author": "Sarah Mitchell", "genre": "contemporary fiction"},
    {"title": "The Lighthouse Keeper", "author": "Sarah Mitchell", "genre": "mystery romance"},
]

REVIEWER_NAMES = [
    "BookLover42", "ReadingWithMaria", "ThrillerFan88", "LitCritic99",
    "NightOwlReader", "PageTurner23", "CoffeeAndBooks", "TheBookworm",
    "AvoidReader", "QuietReading", "LibraryLover", "StoryHunter",
    "WordSmith_Fan", "ChapterChaser", "NovelNerd", "GenreMixer",
    "PlotTwistLover", "BedtimeReader", "CommutReader", "WeekendBinger",
    "MysteryMaven", "RomanceFan", "SciFiGeek", "HistoryBuff",
    "IndieReader", "AudiobookAddict", "KindleKween", "HardcoverOnly",
]

THEMES = ["pacing", "characters", "ending", "plot", "writing_style", "world_building",
           "dialogue", "narration", "editing", "emotional_impact", "value"]

POSITIVE_TEMPLATES = [
    "Absolutely loved this book! The {theme1} was incredible and the {theme2} kept me engaged throughout.",
    "One of the best books I've read this year. The author's {theme1} is masterful.",
    "Couldn't put it down! The {theme1} drew me in from page one. Highly recommend.",
    "A wonderful read. The {theme1} is beautifully crafted and the {theme2} adds such depth.",
    "Five stars! This book exceeded all my expectations. The {theme1} is simply brilliant.",
    "I was completely immersed in this story. The {theme1} and {theme2} work together perfectly.",
    "This is the kind of book that stays with you. Beautiful {theme1} and powerful {theme2}.",
    "Devoured this in one sitting. The {theme1} is top-notch and I loved how the {theme2} unfolded.",
]

MIXED_TEMPLATES = [
    "The {theme1} was good but the {theme2} could have been better. Still an enjoyable read overall.",
    "I had mixed feelings. The first half was strong with great {theme1}, but the {theme2} in the second half didn't work for me.",
    "Three stars. Decent {theme1} but the {theme2} needed more work. Would still recommend to fans of the genre.",
    "Some parts were excellent - particularly the {theme1} - but the {theme2} left me wanting more.",
    "An okay read. The {theme1} was the highlight, though I wished the {theme2} had been more developed.",
]

NEGATIVE_TEMPLATES = [
    "Disappointed. The {theme1} was weak and the {theme2} made it hard to finish.",
    "Not for me. Struggled with the {theme1} throughout and the {theme2} didn't help.",
    "I really wanted to like this but the {theme1} killed it for me. The {theme2} was also problematic.",
    "DNF at 60%. The {theme1} was too slow and the {theme2} wasn't enough to keep me reading.",
    "Below expectations. The {theme1} needed serious work and the {theme2} was predictable.",
]

AI_STYLE_TEMPLATES = [
    "This novel delves into the compelling tapestry of {theme1} with remarkable finesse. The author masterfully weaves together elements of {theme2}, creating a narrative that is both thought-provoking and deeply engaging. Three key strengths emerge: first, the {theme1}; second, the {theme2}; and third, the overall coherence of the story.",
    "A nuanced exploration of {theme1} that demonstrates the author's sophisticated understanding of the genre. The {theme2} serves as a particularly effective device, elevating the work above its contemporaries.",
]

ACTIONABLE_TEMPLATES = [
    "I noticed several typos in chapters 12 and 15. Also, the {theme1} could use revision - the timeline doesn't quite work.",
    "Love the book but the Kindle formatting has issues - chapter breaks are missing in some sections. The {theme1} is otherwise great.",
    "Great story but please fix the continuity error in chapter 8 - the character's eye color changes. The {theme1} was otherwise perfect.",
    "Would love a sequel! The {theme1} left so many questions unanswered. Also, the {theme2} deserves more exploration.",
]


def generate_reviews() -> list[dict]:
    """Generate ~200 synthetic reviews across all books."""
    reviews = []
    now = datetime.now(timezone.utc)

    for book in BOOKS:
        # 20-25 reviews per book
        num_reviews = random.randint(20, 25)

        # Distribution: 60% positive, 25% mixed, 15% negative
        num_positive = int(num_reviews * 0.60)
        num_mixed = int(num_reviews * 0.25)
        num_negative = num_reviews - num_positive - num_mixed

        # 10% AI-style, 20% actionable
        num_ai = max(1, int(num_reviews * 0.10))
        num_actionable = max(2, int(num_reviews * 0.20))

        for i in range(num_reviews):
            theme1, theme2 = random.sample(THEMES, 2)
            days_ago = random.randint(1, 180)
            review_date = (now - timedelta(days=days_ago)).isoformat()

            # Determine type
            if i < num_ai:
                template = random.choice(AI_STYLE_TEMPLATES)
                target_sentiment = random.choice(["positive", "mixed"])
                rating = random.choice([4, 5]) if target_sentiment == "positive" else 3
                is_ai_style = True
                is_actionable = False
            elif i < num_ai + num_actionable:
                template = random.choice(ACTIONABLE_TEMPLATES)
                target_sentiment = random.choice(["positive", "mixed"])
                rating = random.choice([3, 4])
                is_ai_style = False
                is_actionable = True
            elif i < num_ai + num_actionable + num_positive:
                template = random.choice(POSITIVE_TEMPLATES)
                target_sentiment = "positive"
                rating = random.choice([4, 5, 5])
                is_ai_style = False
                is_actionable = False
            elif i < num_ai + num_actionable + num_positive + num_mixed:
                template = random.choice(MIXED_TEMPLATES)
                target_sentiment = "mixed"
                rating = 3
                is_ai_style = False
                is_actionable = False
            else:
                template = random.choice(NEGATIVE_TEMPLATES)
                target_sentiment = "negative"
                rating = random.choice([1, 2])
                is_ai_style = False
                is_actionable = False

            text = template.format(theme1=theme1, theme2=theme2)

            reviews.append({
                "review_id": str(uuid.uuid4()),
                "book_title": book["title"],
                "book_author": book["author"],
                "reviewer_name": random.choice(REVIEWER_NAMES),
                "rating": rating,
                "review_text": text,
                "review_summary": text[:80] + "...",
                "review_date": review_date,
                "verified_purchase": random.random() > 0.3,
                "helpful_votes": random.randint(0, 50),
                "target_sentiment": target_sentiment,
                "target_ai_generated": is_ai_style,
                "target_actionable": is_actionable,
            })

    random.shuffle(reviews)
    return reviews


def main():
    reviews = generate_reviews()
    output_path = DATA_DIR / "seed_reviews.json"
    with open(output_path, "w") as f:
        json.dump(reviews, f, indent=2)

    print(f"Generated {len(reviews)} reviews across {len(BOOKS)} books")
    print(f"Saved to: {output_path}")

    # Summary
    for book in BOOKS:
        count = sum(1 for r in reviews if r["book_title"] == book["title"])
        print(f"  {book['title']}: {count} reviews")


if __name__ == "__main__":
    main()
