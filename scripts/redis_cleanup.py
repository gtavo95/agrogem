#!/usr/bin/env python3
"""
Cleanup script for Redis keys belonging to this service only.
Only touches keys that match KNOWN_KEY_PREFIXES — all other keys are left untouched.

Actions on matched keys:
- Deletes keys with no TTL set (ttl == -1)
- Trims keys with TTL > MAX_TTL_SECONDS down to MAX_TTL_SECONDS

Usage:
    REDIS_URI=redis://... python scripts/redis_cleanup.py [--dry-run]
"""

import asyncio
import os
import sys

import redis.asyncio as aioredis

MAX_TTL_SECONDS = 3600  # 1 hour

KNOWN_KEY_PREFIXES = (
    "elevation:",
    "geocode:fwd:",
    "geocode:rev:",
    "soil:",
    "climate:hist:",
    "chat:session:",
    "gbif:",
    "weather:",
)


async def cleanup(dry_run: bool = False) -> None:
    url = os.environ.get("REDIS_URI")
    if not url:
        print("ERROR: REDIS_URI environment variable not set.", file=sys.stderr)
        sys.exit(1)

    client = aioredis.from_url(url, decode_responses=True)

    try:
        await client.ping()
        print(f"Connected to Redis: {url.split('@')[-1]}")
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis: {e}", file=sys.stderr)
        sys.exit(1)

    total = 0
    skipped = 0
    deleted = 0
    trimmed = 0
    cursor = 0

    print(f"Scanning all keys (dry_run={dry_run})...\n")

    while True:
        cursor, keys = await client.scan(cursor, count=500)
        for key in keys:
            total += 1

            if not key.startswith(KNOWN_KEY_PREFIXES):
                skipped += 1
                continue

            ttl = await client.ttl(key)

            if ttl == -1:
                # Known key with no expiry — delete it
                action = "DELETE (no TTL)"
                if not dry_run:
                    await client.delete(key)
                    deleted += 1
                print(f"  [{action}] {key!r}")

            elif ttl > MAX_TTL_SECONDS:
                # TTL too long — trim it down
                action = f"EXPIRE {ttl}s → {MAX_TTL_SECONDS}s"
                if not dry_run:
                    await client.expire(key, MAX_TTL_SECONDS)
                    trimmed += 1
                print(f"  [{action}] {key!r}")

        if cursor == 0:
            break

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done.")
    print(f"  Total keys scanned       : {total}")
    print(f"  Skipped (other services) : {skipped}")
    print(f"  Deleted (no TTL)         : {deleted if not dry_run else '(dry-run)'}")
    print(f"  TTL trimmed              : {trimmed if not dry_run else '(dry-run)'}")

    await client.aclose()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(cleanup(dry_run=dry_run))
