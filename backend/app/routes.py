import logging
from datetime import date

from flask import Blueprint, jsonify, request

from app import config, db
from app.data.sleeper import provider
from app.data.types import PlayerData
from app.limiter import limiter
from app.llm.cache import get_current_nfl_week, make_cache_key
from app.llm.evaluator import evaluate_trade, resolve_api_key

logger = logging.getLogger(__name__)

bp = Blueprint("api", __name__, url_prefix="/api")

VALID_SCORING = {"ppr", "half", "standard"}
VALID_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}
VALID_INJURY_STATUSES = {
    "Questionable",
    "Doubtful",
    "Out",
    "IR",
    "PUP",
    "Sus",
    "NA",
    "COV",
    "DNR",
}
MAX_NAME_LENGTH = 60
MAX_TEAM_LENGTH = 5
MAX_PLAYERS_PER_SIDE = 10


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/leaderboard")
def leaderboard():
    scoring = request.args.get("scoring", config.DEFAULT_SCORING)
    if scoring not in VALID_SCORING:
        scoring = config.DEFAULT_SCORING

    try:
        board = provider.get_leaderboard(scoring=scoring)
    except Exception:
        logger.exception("Leaderboard fetch failed")
        return jsonify({"error": "Failed to load leaderboard"}), 500

    return jsonify(board)


@bp.get("/players/search")
def search_players():
    query = request.args.get("q", "")
    scoring = request.args.get("scoring", config.DEFAULT_SCORING)
    if scoring not in VALID_SCORING:
        scoring = config.DEFAULT_SCORING

    if not query or len(query.strip()) < 2:
        return jsonify({"players": []})

    try:
        players = provider.search_players(query, limit=20, scoring=scoring)
    except Exception:
        logger.exception("Player search failed")
        return jsonify({"error": "Failed to search players"}), 500

    return jsonify({"players": [p.to_dict() for p in players]})


def _compute_value_gap(team_a: list[PlayerData], team_b: list[PlayerData], players: list) -> dict:
    """Deterministically sums each side's adjFantasyPts and the percent gap
    between them. This is plain arithmetic on numbers the LLM already
    returned -- never delegated to the model itself.

    Convention: team_a/team_b list the players each side GIVES UP. So Team A
    RECEIVES the team_b players, and Team B receives the team_a players --
    teamAReceives sums adjFantasyPts of players whose name is in team_b, and
    teamBReceives sums those whose name is in team_a.
    """
    a_gives_names = {p.name.strip().lower() for p in team_a}
    b_gives_names = {p.name.strip().lower() for p in team_b}

    def sum_by_name():
        a_receives = b_receives = 0.0
        matched = 0
        for entry in players:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip().lower()
            adj = entry.get("adjFantasyPts")
            if adj is None:
                continue
            if name in a_gives_names:
                b_receives += float(adj)
                matched += 1
            elif name in b_gives_names:
                a_receives += float(adj)
                matched += 1
        return a_receives, b_receives, matched

    team_a_receives, team_b_receives, matched = sum_by_name()

    # Fall back to positional mapping (teamA's given-up players first, then
    # teamB's) if name matching didn't account for every entry but the counts
    # line up -- the model may have altered a name slightly.
    if matched < len(players) and len(players) == len(team_a) + len(team_b):
        # players[:len(team_a)] are what team_a gave up -> team_b receives them.
        team_b_receives = sum(
            float(p.get("adjFantasyPts") or 0) for p in players[: len(team_a)] if isinstance(p, dict)
        )
        team_a_receives = sum(
            float(p.get("adjFantasyPts") or 0) for p in players[len(team_a) :] if isinstance(p, dict)
        )

    higher = max(team_a_receives, team_b_receives)
    percent_gap = (abs(team_a_receives - team_b_receives) / higher * 100) if higher > 0 else 0.0

    return {
        "teamAReceives": round(team_a_receives, 2),
        "teamBReceives": round(team_b_receives, 2),
        "percentGap": round(percent_gap, 2),
    }


def _reconcile_winner(result: dict, value_gap: dict) -> None:
    """Safety net: the model has occasionally inverted which side receives
    more (its own "winner" field disagreeing with the deterministic
    valueGap totals we just computed). Only correct outright wrong-side
    calls -- never overrule a judgment call of "even", and never flip an
    already-correct A/B answer.
    """
    a = value_gap["teamAReceives"]
    b = value_gap["teamBReceives"]
    winner = result.get("winner")
    corrected = None
    if winner == "A" and b > a:
        corrected = "B"
    elif winner == "B" and a > b:
        corrected = "A"
    if corrected:
        logger.warning(
            "Model's winner (%s) contradicted computed totals (A receives %.2f, B receives %.2f); correcting to %s",
            winner,
            a,
            b,
            corrected,
        )
        result["winner"] = corrected


def _parse_player_list(raw_list, field_name: str) -> list[PlayerData]:
    """Validates a strict, structured player list -- name/position/etc. are
    checked against known shapes and bounded lengths so a client can never
    smuggle an arbitrary free-text prompt into the request that reaches the
    model on the server's key.
    """
    if not isinstance(raw_list, list) or len(raw_list) == 0:
        raise ValueError(f"'{field_name}' must be a non-empty list of players")
    if len(raw_list) > MAX_PLAYERS_PER_SIDE:
        raise ValueError(f"'{field_name}' cannot have more than {MAX_PLAYERS_PER_SIDE} players")

    players = []
    for item in raw_list:
        if not isinstance(item, dict):
            raise ValueError(f"'{field_name}' contains a non-object player entry")

        name = item.get("name")
        if not name or not isinstance(name, str) or len(name) > MAX_NAME_LENGTH:
            raise ValueError(f"'{field_name}' has a player with an invalid 'name'")

        position = item.get("position")
        if position not in VALID_POSITIONS:
            raise ValueError(f"'{field_name}' has a player with invalid position: {position}")

        team = item.get("team")
        if team is not None and (not isinstance(team, str) or len(team) > MAX_TEAM_LENGTH):
            raise ValueError(f"'{field_name}' has a player with an invalid 'team'")

        injury_status = item.get("injuryStatus")
        if injury_status is not None and injury_status not in VALID_INJURY_STATUSES:
            raise ValueError(f"'{field_name}' has a player with an unrecognized injuryStatus")

        players.append(PlayerData.from_dict(item))
    return players


def _split_cached_players(
    team: list[PlayerData], week: int, scoring: str
) -> tuple[list[dict], list[PlayerData]]:
    """Per-player projection cache lookup: players already adjusted this week
    (regardless of which trade they appeared in -- a player's news-driven
    adjustment doesn't depend on his trade partners) come back as read-only
    context; everyone else needs a fresh LLM look."""
    context: list[dict] = []
    new: list[PlayerData] = []
    for player in team:
        cached = db.get_cached_projection(player.id, week, scoring)
        if cached:
            context.append(cached)
        else:
            new.append(player)
    return context, new


def _merge_players(
    team_a: list[PlayerData],
    team_b: list[PlayerData],
    team_a_context: list[dict],
    team_b_context: list[dict],
    new_entries: list,
) -> list[dict]:
    """Reassembles the full per-player breakdown in original roster order,
    combining fresh LLM output with reused per-player cache entries -- the
    model was only asked to return entries for the new players."""
    context_by_name = {c["name"].strip().lower(): c for c in team_a_context + team_b_context if c.get("name")}
    new_by_name = {
        str(e.get("name", "")).strip().lower(): e for e in new_entries if isinstance(e, dict) and e.get("name")
    }

    merged = []
    for player in team_a + team_b:
        key = player.name.strip().lower()
        if key in context_by_name:
            c = context_by_name[key]
            merged.append(
                {
                    "name": c.get("name", player.name),
                    "projFantasyPts": c.get("projFantasyPts", player.projFantasyPts),
                    "adjFantasyPts": c.get("adjFantasyPts", player.projFantasyPts),
                    "adjustmentReason": c.get("adjustmentReason", ""),
                    "riskFlags": c.get("riskFlags", []),
                }
            )
        elif key in new_by_name:
            merged.append(new_by_name[key])
        else:
            # Defensive fallback: the model dropped this player -- surface
            # the unadjusted baseline rather than silently losing them.
            merged.append(
                {
                    "name": player.name,
                    "projFantasyPts": player.projFantasyPts,
                    "adjFantasyPts": player.projFantasyPts,
                    "adjustmentReason": "No adjustment available.",
                    "riskFlags": [],
                }
            )
    return merged


def _store_new_projections(new_players: list[PlayerData], new_entries: list, week: int, scoring: str) -> None:
    by_name = {p.name.strip().lower(): p for p in new_players}
    for entry in new_entries:
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        player = by_name.get(str(entry["name"]).strip().lower())
        if not player:
            continue
        db.store_projection(
            player.id,
            week,
            scoring,
            {
                "name": entry.get("name", player.name),
                "team": player.team,
                "position": player.position,
                "projFantasyPts": entry.get("projFantasyPts", player.projFantasyPts),
                "adjFantasyPts": entry.get("adjFantasyPts", player.projFantasyPts),
                "adjustmentReason": entry.get("adjustmentReason", ""),
                "riskFlags": entry.get("riskFlags", []),
            },
        )


@bp.post("/evaluate")
@limiter.limit(config.EVAL_RATE_LIMIT)
def evaluate():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    scoring = body.get("scoring", config.DEFAULT_SCORING)
    if scoring not in VALID_SCORING:
        return jsonify({"error": f"'scoring' must be one of {sorted(VALID_SCORING)}"}), 400

    try:
        team_a = _parse_player_list(body.get("teamA"), "teamA")
        team_b = _parse_player_list(body.get("teamB"), "teamB")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    user_api_key = body.get("apiKey")
    if not isinstance(user_api_key, str) or not user_api_key.strip():
        user_api_key = None

    week = get_current_nfl_week()
    cache_key = make_cache_key([p.name for p in team_a], [p.name for p in team_b], scoring, week)

    # 1. Global verdict cache -- shared across all users, checked before
    # anything else. A hit costs nothing and doesn't touch quota.
    try:
        cached_verdict = db.get_cached_verdict(cache_key)
    except Exception:
        logger.exception("Verdict cache lookup failed; continuing without cache")
        cached_verdict = None

    if cached_verdict is not None:
        return jsonify({**cached_verdict, "cached": True})

    # 2. Daily free-tier quota -- only enforced when using the server's key.
    # BYOK requests are the user's own cost and skip this entirely.
    client_ip = request.remote_addr or "unknown"
    today = date.today()
    if user_api_key is None:
        try:
            used = db.get_quota_count(client_ip, today)
        except Exception:
            logger.exception("Quota lookup failed; failing open for this request")
            used = 0
        if used >= config.FREE_EVALS_PER_USER_PER_DAY:
            return (
                jsonify(
                    {
                        "error": (
                            f"Daily free evaluation limit ({config.FREE_EVALS_PER_USER_PER_DAY}) reached. "
                            "Try again tomorrow, or provide your own OpenAI API key."
                        )
                    }
                ),
                429,
            )

    try:
        resolve_api_key(user_api_key)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    # 3. Per-player projection cache -- skip re-researching players already
    # adjusted this week in some other trade.
    team_a_context, team_a_new = _split_cached_players(team_a, week, scoring)
    team_b_context, team_b_new = _split_cached_players(team_b, week, scoring)

    try:
        trending_ids = provider.get_trending_player_ids()
    except Exception:
        logger.exception("Trending player fetch failed; treating as empty")
        trending_ids = set()

    try:
        result = evaluate_trade(
            team_a_new,
            team_b_new,
            team_a_context,
            team_b_context,
            scoring,
            api_key=user_api_key,
            trending_ids=trending_ids,
        )
    except ValueError as exc:
        logger.error("LLM parse failure: %s", exc)
        return jsonify({"error": f"Failed to get a valid evaluation from the model: {exc}"}), 500
    except Exception as exc:
        logger.exception("LLM evaluation failed")
        return jsonify({"error": f"Trade evaluation failed: {exc}"}), 500

    if user_api_key is None:
        try:
            db.increment_quota(client_ip, today)
        except Exception:
            logger.exception("Quota increment failed (non-fatal)")

    try:
        _store_new_projections(team_a_new + team_b_new, result.get("players", []), week, scoring)
    except Exception:
        logger.exception("Per-player projection cache write failed (non-fatal)")

    full_players = _merge_players(team_a, team_b, team_a_context, team_b_context, result.get("players", []))
    result["players"] = full_players
    result["valueGap"] = _compute_value_gap(team_a, team_b, full_players)
    _reconcile_winner(result, result["valueGap"])

    try:
        db.store_verdict(cache_key, result, week)
    except Exception:
        logger.exception("Verdict cache write failed (non-fatal)")

    return jsonify({**result, "cached": False})
