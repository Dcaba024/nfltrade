import json
import logging
import os
import time
from typing import Optional

import requests

from app import config
from app.data.types import PlayerData

logger = logging.getLogger(__name__)

SCORING_STAT_KEY = {
    "ppr": "pts_ppr",
    "half": "pts_half_ppr",
    "standard": "pts_std",
}


class SleeperProvider:
    """Provider-agnostic adapter over the free Sleeper NFL API.

    Player metadata (~5MB) is cached to a local JSON file and refreshed at
    most once/day. Weekly projections are cached per (season, week, scoring)
    and refreshed hourly. This local-file cache is a stand-in for a future
    Postgres-backed cache -- callers only see the `get_*` methods below, so
    swapping the storage layer later won't require changes elsewhere.
    """

    def __init__(self):
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        self._players: Optional[dict] = None
        self._projections_cache: dict[str, dict] = {}
        self._season_stats_cache: dict[int, dict] = {}
        self._leaderboard_cache: dict[tuple, tuple[float, dict]] = {}
        self._trending_cache: tuple[float, set] = (0.0, set())

    # -- players -----------------------------------------------------------

    def _players_cache_is_fresh(self) -> bool:
        if not os.path.exists(config.PLAYERS_CACHE_FILE):
            return False
        age = time.time() - os.path.getmtime(config.PLAYERS_CACHE_FILE)
        return age < config.PLAYERS_CACHE_MAX_AGE_SECONDS

    def _fetch_players_from_api(self) -> dict:
        logger.info("Fetching Sleeper player metadata from API (daily refresh)")
        resp = requests.get(f"{config.SLEEPER_BASE_URL}/players/nfl", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        with open(config.PLAYERS_CACHE_FILE, "w") as f:
            json.dump(data, f)
        return data

    def _load_players(self) -> dict:
        if self._players is not None:
            return self._players
        if self._players_cache_is_fresh():
            with open(config.PLAYERS_CACHE_FILE, "r") as f:
                self._players = json.load(f)
        else:
            try:
                self._players = self._fetch_players_from_api()
            except requests.RequestException:
                logger.exception("Failed to fetch Sleeper players; falling back to stale cache if present")
                if os.path.exists(config.PLAYERS_CACHE_FILE):
                    with open(config.PLAYERS_CACHE_FILE, "r") as f:
                        self._players = json.load(f)
                else:
                    raise
        return self._players

    # -- projections ---------------------------------------------------------

    def _projections_cache_file(self, season: int, week: int) -> str:
        return os.path.join(config.CACHE_DIR, f"projections_{season}_wk{week}.json")

    def _projections_cache_is_fresh(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        age = time.time() - os.path.getmtime(path)
        return age < config.PROJECTIONS_CACHE_MAX_AGE_SECONDS

    def _fetch_projections_from_api(self, season: int, week: int) -> list:
        logger.info("Fetching Sleeper projections for season=%s week=%s", season, week)
        url = f"{config.SLEEPER_PROJECTIONS_BASE_URL}/{season}/{week}"
        resp = requests.get(url, params={"season_type": "regular"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        path = self._projections_cache_file(season, week)
        with open(path, "w") as f:
            json.dump(data, f)
        return data

    def _load_projections(self, season: int, week: int) -> dict:
        """Returns a dict keyed by player_id -> projection entry."""
        cache_key = f"{season}_{week}"
        if cache_key in self._projections_cache:
            return self._projections_cache[cache_key]

        path = self._projections_cache_file(season, week)
        raw = None
        if self._projections_cache_is_fresh(path):
            with open(path, "r") as f:
                raw = json.load(f)
        else:
            try:
                raw = self._fetch_projections_from_api(season, week)
            except requests.RequestException:
                logger.exception("Failed to fetch Sleeper projections; falling back to stale cache if present")
                if os.path.exists(path):
                    with open(path, "r") as f:
                        raw = json.load(f)
                else:
                    raw = []

        by_id = {}
        for entry in raw or []:
            player_id = entry.get("player_id")
            if player_id is not None:
                by_id[str(player_id)] = entry
        self._projections_cache[cache_key] = by_id
        return by_id

    # -- image resolution ------------------------------------------------

    def _image_url(self, player_id: str, position: str, team: Optional[str]) -> str:
        if position == "DEF":
            # Defenses have no individual headshot; use the team logo. For DEF
            # entries Sleeper's player_id is the team abbreviation itself.
            team_abbr = team or player_id
            return f"{config.SLEEPER_TEAM_LOGO_URL}/{team_abbr}.png"
        return f"{config.SLEEPER_CDN_THUMB_URL}/{player_id}.jpg"

    # -- public API --------------------------------------------------------

    def _display_name(self, player_id: str, meta: dict, position: str, team: Optional[str]) -> str:
        if position == "DEF":
            return meta.get("last_name") or meta.get("first_name") or team or player_id
        first = meta.get("first_name", "")
        last = meta.get("last_name", "")
        return f"{first} {last}".strip() or meta.get("full_name", "") or player_id

    def _build_player_data(
        self, player_id: str, meta: dict, projections_by_id: dict, scoring: str
    ) -> PlayerData:
        position = meta.get("position") or (meta.get("fantasy_positions") or [None])[0] or ""
        team = meta.get("team")
        name = self._display_name(player_id, meta, position, team)

        projection = projections_by_id.get(player_id, {})
        stats = projection.get("stats", {}) or {}

        stat_key = SCORING_STAT_KEY.get(scoring, SCORING_STAT_KEY["ppr"])
        proj_pts = stats.get(stat_key)
        if proj_pts is None:
            proj_pts = stats.get("pts_ppr", 0) or 0

        proj_yards = (
            (stats.get("rec_yd") or 0)
            + (stats.get("rush_yd") or 0)
            + (stats.get("pass_yd") or 0)
        )
        proj_tds = (
            (stats.get("rec_td") or 0)
            + (stats.get("rush_td") or 0)
            + (stats.get("pass_td") or 0)
        )

        opponent = projection.get("opponent")

        return PlayerData(
            id=player_id,
            name=name,
            team=team,
            position=position,
            opponent=opponent,
            injuryStatus=meta.get("injury_status"),
            projFantasyPts=round(float(proj_pts), 2),
            projYards=round(float(proj_yards), 1),
            projTDs=round(float(proj_tds), 2),
            imageUrl=self._image_url(player_id, position, team),
        )

    def search_players(
        self,
        query: str,
        limit: int = 20,
        scoring: str = "ppr",
        season: Optional[int] = None,
        week: Optional[int] = None,
    ) -> list[PlayerData]:
        season = season or config.CURRENT_SEASON
        week = week or config.CURRENT_WEEK

        players = self._load_players()
        projections_by_id = self._load_projections(season, week)

        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for player_id, meta in players.items():
            if not meta:
                continue
            position = meta.get("position") or ""
            if position not in ("QB", "RB", "WR", "TE", "K", "DEF"):
                continue
            first = (meta.get("first_name") or "")
            last = (meta.get("last_name") or "")
            full_name = f"{first} {last}".strip().lower()
            if query_lower not in full_name:
                continue
            matches.append((player_id, meta))

        # Prefer players who are actually on a team and rank shorter/closer
        # name matches first, then fall back to projected points.
        def sort_key(item):
            player_id, meta = item
            has_team = 1 if meta.get("team") else 0
            projection = projections_by_id.get(player_id, {})
            pts = (projection.get("stats") or {}).get("pts_ppr", 0) or 0
            return (-has_team, -pts)

        matches.sort(key=sort_key)
        matches = matches[:limit]

        return [
            self._build_player_data(player_id, meta, projections_by_id, scoring)
            for player_id, meta in matches
        ]

    def get_players_by_ids(
        self,
        player_ids: list[str],
        scoring: str = "ppr",
        season: Optional[int] = None,
        week: Optional[int] = None,
    ) -> list[PlayerData]:
        season = season or config.CURRENT_SEASON
        week = week or config.CURRENT_WEEK

        players = self._load_players()
        projections_by_id = self._load_projections(season, week)

        results = []
        for player_id in player_ids:
            meta = players.get(player_id)
            if not meta:
                continue
            results.append(self._build_player_data(player_id, meta, projections_by_id, scoring))
        return results

    # -- season stats / leaderboard -----------------------------------------

    def _season_stats_cache_file(self, season: int) -> str:
        return os.path.join(config.CACHE_DIR, f"season_stats_{season}.json")

    def _season_stats_cache_is_fresh(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        age = time.time() - os.path.getmtime(path)
        return age < config.SEASON_STATS_CACHE_MAX_AGE_SECONDS

    def _fetch_season_stats_from_api(self, season: int) -> list:
        logger.info("Fetching Sleeper season-to-date stats for season=%s", season)
        url = f"{config.SLEEPER_STATS_BASE_URL}/{season}"
        resp = requests.get(url, params={"season_type": "regular"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        path = self._season_stats_cache_file(season)
        with open(path, "w") as f:
            json.dump(data, f)
        return data

    def _load_season_stats(self, season: int) -> dict:
        """Returns a dict keyed by player_id -> stats dict (pts_ppr, etc.)."""
        if season in self._season_stats_cache:
            return self._season_stats_cache[season]

        path = self._season_stats_cache_file(season)
        raw = None
        if self._season_stats_cache_is_fresh(path):
            with open(path, "r") as f:
                raw = json.load(f)
        else:
            try:
                raw = self._fetch_season_stats_from_api(season)
            except requests.RequestException:
                logger.exception("Failed to fetch Sleeper season stats; falling back to stale cache if present")
                if os.path.exists(path):
                    with open(path, "r") as f:
                        raw = json.load(f)
                else:
                    raw = []

        by_id = {}
        for entry in raw or []:
            if not entry:
                continue
            player_id = entry.get("player_id")
            stats = entry.get("stats")
            if player_id is None or not stats:
                continue
            by_id[str(player_id)] = stats
        self._season_stats_cache[season] = by_id
        return by_id

    def get_leaderboard(self, scoring: str = "ppr", season: Optional[int] = None) -> dict:
        """Top LEADERBOARD_TOP_N scorers per position, sorted descending.

        Cached in-memory per (season, scoring) and refreshed roughly hourly --
        the underlying season stats fetch is itself hourly-cached to disk, but
        we also skip re-grouping/sorting ~8k entries on every request.
        """
        season = season or config.CURRENT_SEASON
        cache_key = (season, scoring)
        now = time.time()
        cached = self._leaderboard_cache.get(cache_key)
        if cached and (now - cached[0]) < config.LEADERBOARD_CACHE_MAX_AGE_SECONDS:
            return cached[1]

        players = self._load_players()
        stats_by_id = self._load_season_stats(season)
        stat_key = SCORING_STAT_KEY.get(scoring, SCORING_STAT_KEY["ppr"])

        grouped: dict[str, list[tuple[float, str, dict]]] = {
            position: [] for position in config.LEADERBOARD_POSITIONS
        }
        for player_id, stats in stats_by_id.items():
            pts = stats.get(stat_key)
            if pts is None:
                continue
            meta = players.get(player_id)
            if not meta:
                continue
            position = meta.get("position") or (meta.get("fantasy_positions") or [None])[0]
            if position not in grouped:
                continue
            grouped[position].append((float(pts), player_id, meta))

        result: dict[str, list[dict]] = {}
        for position, entries in grouped.items():
            entries.sort(key=lambda e: e[0], reverse=True)
            top = entries[: config.LEADERBOARD_TOP_N]
            rows = []
            for rank, (pts, player_id, meta) in enumerate(top, start=1):
                team = meta.get("team")
                rows.append(
                    {
                        "rank": rank,
                        "name": self._display_name(player_id, meta, position, team),
                        "team": team,
                        "position": position,
                        "imageUrl": self._image_url(player_id, position, team),
                        "points": round(pts, 2),
                    }
                )
            result[position] = rows

        self._leaderboard_cache[cache_key] = (now, result)
        return result

    # -- trending ------------------------------------------------------------

    def get_trending_player_ids(self) -> set:
        """Player IDs on Sleeper's trending-add list, cached in-memory for an
        hour. Used to decide whether a trade needs a fresh web search (a
        trending player's situation is more likely to have changed recently)
        without spending a search on every healthy, unremarkable player.
        """
        now = time.time()
        fetched_at, ids = self._trending_cache
        if ids and (now - fetched_at) < config.TRENDING_CACHE_MAX_AGE_SECONDS:
            return ids

        try:
            resp = requests.get(config.SLEEPER_TRENDING_URL, params={"lookback_hours": 24, "limit": 50}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            ids = {str(entry["player_id"]) for entry in data if entry.get("player_id")}
            self._trending_cache = (now, ids)
            return ids
        except (requests.RequestException, KeyError, ValueError, TypeError):
            logger.exception("Failed to fetch Sleeper trending players; falling back to stale/empty set")
            return ids


# Module-level singleton -- fine for a stateless single-process dev server.
provider = SleeperProvider()
