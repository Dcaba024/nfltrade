import hashlib
import json
import logging
import time
from typing import Optional

import requests

from app import config

logger = logging.getLogger(__name__)

_state_cache: dict = {"week": None, "fetched_at": 0.0}


def get_current_nfl_week() -> int:
    """Returns the current NFL week per Sleeper's state endpoint, cached in
    memory (and refreshed hourly) so the cache-key lookup doesn't hit the
    network on every /api/evaluate call. Falls back to the date-heuristic
    week in config if the request fails and nothing is cached yet.
    """
    now = time.time()
    if _state_cache["week"] is not None and (now - _state_cache["fetched_at"]) < config.NFL_STATE_CACHE_MAX_AGE_SECONDS:
        return _state_cache["week"]

    try:
        resp = requests.get(config.SLEEPER_STATE_URL, timeout=10)
        resp.raise_for_status()
        week = int(resp.json()["week"])
        _state_cache["week"] = week
        _state_cache["fetched_at"] = now
        return week
    except (requests.RequestException, KeyError, ValueError, TypeError):
        logger.exception("Failed to fetch Sleeper NFL state; falling back to date-heuristic week")
        if _state_cache["week"] is not None:
            return _state_cache["week"]
        return config.CURRENT_WEEK


# What adjFantasyPts measures. Bumped from the original this-week-only basis
# to rest-of-season points per game; part of every cache key so cached
# numbers from an older basis are never mixed into a newer evaluation.
VALUE_BASIS = "ros-v1"


def projection_cache_scope(scoring: str) -> str:
    """Scoring column value for the per-player projection cache."""
    return f"{scoring}:{VALUE_BASIS}"


def make_cache_key(
    team_a_names: list[str],
    team_b_names: list[str],
    scoring: str,
    week: int,
    roster: Optional[dict] = None,
) -> str:
    """Order-independent key: two trades with the same players on each side
    (regardless of the order they were added) and the same scoring/week hash
    to the same key. Shared across all users -- this is a global cache, not
    per-session. A trade judged against a user's roster carries a
    roster-specific rosterFit, so the roster (side + player ids/slots) is
    part of the key when present.
    """
    payload = {
        "teamA": sorted(name.strip().lower() for name in team_a_names),
        "teamB": sorted(name.strip().lower() for name in team_b_names),
        "scoring": scoring,
        "week": week,
        "basis": VALUE_BASIS,
    }
    if roster:
        payload["roster"] = {"side": roster["side"], "players": sorted(f"{p.id}:{slot}" for p, slot in roster["players"])}
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
