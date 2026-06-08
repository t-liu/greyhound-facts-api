#!/usr/bin/env python3
"""Seed script: populate the DynamoDB table with initial greyhound facts.

Usage:
    python scripts/seed.py [--env local|dev|prod]

Reads configuration from environment variables (or .env file).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.models.request import CreateFactRequest  # noqa: E402
from app.repositories.dynamodb_repository import DynamoDBRepository  # noqa: E402
from app.services.fact_service import FactService  # noqa: E402

logger = logging.getLogger(__name__)

FACTS: list[dict] = [
    {
        "text": "Greyhounds can reach top speeds of 40–45 mph (64–72 km/h), making them the fastest dog breed in the world.",
        "source": "American Kennel Club",
        "tags": ["speed", "physiology"],
    },
    {
        "text": "Despite their racing reputation, Greyhounds are nicknamed '45-mph couch potatoes' because they love to sleep and lounge for up to 18 hours a day.",
        "source": "Greyhound Pets of America",
        "tags": ["temperament", "behavior"],
    },
    {
        "text": "Greyhounds have an extremely low body-fat percentage (around 16%) and very thin skin, which is why they need coats in cold weather.",
        "source": "Veterinary Practice News",
        "tags": ["physiology", "health"],
    },
    {
        "text": "A Greyhound's heart is disproportionately large compared to other breeds — it can pump up to 5 gallons of blood per minute at full sprint.",
        "source": "Journal of Veterinary Internal Medicine",
        "tags": ["physiology", "heart"],
    },
    {
        "text": "Greyhounds have a 270-degree field of vision due to the placement of their eyes, giving them a wider view than humans (180°).",
        "source": "AKC Breed Standards",
        "tags": ["physiology", "vision"],
    },
    {
        "text": "The Greyhound is one of the oldest dog breeds, with depictions found in Egyptian tomb art dating back to 2900 BC.",
        "source": "Smithsonian Magazine",
        "tags": ["history", "origin"],
    },
    {
        "text": "Greyhounds are the only dog breed specifically mentioned in the Bible (Proverbs 30:31 in the King James Version).",
        "source": "King James Bible, Proverbs 30:31",
        "tags": ["history", "trivia"],
    },
    {
        "text": "Unlike most dogs, Greyhounds lack a significant undercoat, making them sensitive to temperature extremes but also hypoallergenic for many allergy sufferers.",
        "source": "American College of Veterinary Dermatology",
        "tags": ["physiology", "health"],
    },
    {
        "text": "Greyhounds are 'double-suspension galloping' dogs: all four feet leave the ground twice per stride, which is key to their extraordinary speed.",
        "source": "Canine Locomotion Research Institute",
        "tags": ["speed", "physiology", "gait"],
    },
    {
        "text": "The average lifespan of a Greyhound is 10–14 years, and many retired racing Greyhounds make gentle, affectionate family pets.",
        "source": "Greyhound Adoption Network",
        "tags": ["lifespan", "adoption", "temperament"],
    },
]


def seed(dry_run: bool = False) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "Seeding %d facts into table '%s' (env=%s, dry_run=%s).",
        len(FACTS),
        settings.dynamodb_table_name,
        settings.app_env,
        dry_run,
    )

    if dry_run:
        logger.info("Dry-run mode — no writes performed.")
        return

    repo = DynamoDBRepository(settings)
    service = FactService(repo)

    success = 0
    for raw in FACTS:
        payload = CreateFactRequest(**raw)
        try:
            fact = service.create_fact(payload)
            logger.info("Seeded fact id=%s: %.60s…", fact.id, fact.text)
            success += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipped (already exists or error): %s — %s", raw["text"][:50], exc)

    logger.info("Seeding complete. %d/%d facts written.", success, len(FACTS))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed greyhound facts into DynamoDB.")
    parser.add_argument("--dry-run", action="store_true", help="Log what would be seeded without writing.")
    args = parser.parse_args()
    seed(dry_run=args.dry_run)
