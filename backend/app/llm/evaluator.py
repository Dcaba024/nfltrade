import json
import logging
import re
from typing import Optional

from openai import OpenAI

from app import config
from app.data.types import PlayerData

logger = logging.getLogger(__name__)

# Cost-control knobs -- single swappable constants (sourced from config/env,
# never hardcoded below) so the model tier, reasoning effort, web-search cap,
# and free-tier quota are trivial to tune without touching call sites.
MODEL = config.OPENAI_MODEL
REASONING_EFFORT = config.OPENAI_REASONING_EFFORT
MAX_TOOL_CALLS = config.OPENAI_MAX_TOOL_CALLS
FREE_EVALS_PER_USER_PER_DAY = config.FREE_EVALS_PER_USER_PER_DAY
INJURED = config.INJURED_STATUSES


def resolve_api_key(user_api_key: Optional[str] = None) -> str:
    """BYOK resolution: the caller's own key wins if provided, else the
    server's (demo-allowance, quota-limited) key, else reject. No global
    client/key is read inside the call path itself -- everything flows
    through this one function so swapping in a real per-user key store later
    is a small change.
    """
    if user_api_key:
        return user_api_key
    if config.OPENAI_API_KEY:
        return config.OPENAI_API_KEY
    raise RuntimeError(
        "No OpenAI API key available. Provide your own key, or set OPENAI_API_KEY in backend/.env."
    )


# Terse instructions + a bare schema skeleton -- see README for the fuller
# rationale. Kept byte-identical across calls (nothing per-request is
# interpolated into this string) so it sits as a stable prefix for OpenAI's
# automatic prompt caching.
SYSTEM_PROMPT = """Fantasy football trade analyst. projFantasyPts/projYards/projTDs are ground-truth baselines from a stats provider -- never invented.

Input has teamA_receives and teamB_receives: the players each side RECEIVES in this trade, already assigned to the receiving side (do not swap them -- teamA_receives belongs to Team A's total, not Team B's). Each has two buckets:
- toEvaluate: research (web search) and adjust these.
- alreadyEvaluated: adjFantasyPts is FINAL from a prior evaluation this week. Do not change it or re-explain it. Use it only for totals.

Rules:
- adjFantasyPts = projFantasyPts + a reasoned delta from real, cited news/injury/matchup/usage. No relevant news -> keep near baseline, say so.
- Never fabricate injuries/news. Uncertain -> small or zero adjustment.
- Web search AT MOST ONCE total (one query covering every toEvaluate player), then stop and reason from what you found.
- Sum each side's own receives-total: toEvaluate + alreadyEvaluated adjFantasyPts within teamA_receives = Team A's total; same for teamB_receives = Team B's total. winner = whichever total is higher; "even" only if the two totals are within ~1% of each other.
- fairnessScore (0-100, 100=perfectly even) starts from the raw % gap between the two receives-totals, then adjust for positional scarcity, consolidation (N-for-1 favors the side getting the single best player), injury risk, and bye-week conflicts. If it diverges from the raw gap, say why in fairnessRationale.
- Grade: 90-100 Even, 75-89 Fair, 55-74 Slight Edge, 30-54 Lopsided, 0-29 Unfair.
- rationale, adjustmentReason, fairnessRationale: max 1-2 sentences each.
- "players": one entry per toEvaluate player (from either bucket), NONE for alreadyEvaluated players. Empty toEvaluate -> "players": [].
- Output ONLY this JSON. No markdown fences, no other text.

{"winner":"A|B|even","confidence":0-1,"marginDescription":"","players":[{"name":"","projFantasyPts":0,"adjFantasyPts":0,"adjustmentReason":"","riskFlags":[""]}],"rationale":"","fairnessScore":0-100,"fairnessGrade":"Even|Fair|Slight Edge|Lopsided|Unfair","fairnessRationale":""}"""


def _format_new_entry(player: PlayerData) -> dict:
    return {
        "name": player.name,
        "team": player.team,
        "position": player.position,
        "opponent": player.opponent,
        "injuryStatus": player.injuryStatus,
        "projFantasyPts": player.projFantasyPts,
        "projYards": player.projYards,
        "projTDs": player.projTDs,
    }


def _format_context_entry(cached: dict) -> dict:
    # Trimmed further than the stored cache record -- the model only needs
    # enough to total up the full per-side points, not the full explanation.
    return {
        "name": cached.get("name"),
        "team": cached.get("team"),
        "position": cached.get("position"),
        "adjFantasyPts": cached.get("adjFantasyPts"),
    }


def _build_user_prompt(
    team_a_new: list[PlayerData],
    team_b_new: list[PlayerData],
    team_a_context: list[dict],
    team_b_context: list[dict],
    scoring: str,
) -> str:
    # team_a_new/team_a_context are players Team A GIVES UP -- so they land
    # in teamB_receives, and vice versa. Pre-swapping here (rather than
    # asking the model to do it) removes an inversion the model was getting
    # wrong: it would sometimes attribute a "*_gives" bucket to its own
    # team's total instead of the other side's, silently flipping the
    # winner. Presenting buckets already labeled by who receives them needs
    # no swap on the model's part at all.
    payload: dict = {
        "scoringFormat": scoring,
        "toEvaluate": {
            "teamA_receives": [_format_new_entry(p) for p in team_b_new],
            "teamB_receives": [_format_new_entry(p) for p in team_a_new],
        },
    }
    if team_a_context or team_b_context:
        payload["alreadyEvaluated"] = {
            "teamA_receives": [_format_context_entry(c) for c in team_b_context],
            "teamB_receives": [_format_context_entry(c) for c in team_a_context],
        }
    # Compact separators (no indent/spacing) -- shaves real tokens off a
    # payload that's otherwise identical JSON.
    compact = json.dumps(payload, separators=(",", ":"))
    return f"Evaluate this trade. {compact}"


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def _extract_output_text(response) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    # Fallback: walk the output items manually if the SDK helper isn't present.
    chunks = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                chunks.append(value)
    return "\n".join(chunks)


def needs_web_search(players: list[PlayerData], trending_ids: set) -> bool:
    """Only pay for web search when it can plausibly change the answer: a
    player who's hurt/questionable, or trending (news likely broke
    recently). A trade of healthy, unremarkable starters skips search
    entirely. Players already resolved via the per-player cache never reach
    this check -- only genuinely new players do.
    """
    for p in players:
        if p.injuryStatus in INJURED:
            return True
        if p.id in trending_ids:
            return True
    return False


def _call_openai(user_prompt: str, api_key: str, use_web_search: bool):
    client = OpenAI(api_key=api_key)
    kwargs = dict(
        model=MODEL,
        reasoning={"effort": REASONING_EFFORT},
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    if use_web_search:
        kwargs["tools"] = [{"type": "web_search"}]
        kwargs["max_tool_calls"] = MAX_TOOL_CALLS
    return client.responses.create(**kwargs)


def evaluate_trade(
    team_a_new: list[PlayerData],
    team_b_new: list[PlayerData],
    team_a_context: list[dict],
    team_b_context: list[dict],
    scoring: str,
    api_key: Optional[str] = None,
    trending_ids: Optional[set] = None,
) -> dict:
    """Calls the OpenAI Responses API to adjust projections for the *new*
    players and render a trade verdict over the combined (new + cached
    context) totals. Retries once if the model's response isn't parseable
    JSON. `team_a_new`/`team_b_new` are the players needing fresh research;
    `team_a_context`/`team_b_context` are already-adjusted cache hits
    provided as read-only context.
    """
    resolved_key = resolve_api_key(api_key)
    user_prompt = _build_user_prompt(team_a_new, team_b_new, team_a_context, team_b_context, scoring)
    use_web_search = needs_web_search(team_a_new + team_b_new, trending_ids or set())

    last_error = None
    last_raw_text = None
    for attempt in range(2):
        response = _call_openai(user_prompt, resolved_key, use_web_search)
        raw_text = _extract_output_text(response)
        last_raw_text = raw_text
        cleaned = _strip_markdown_fences(raw_text)
        try:
            parsed = json.loads(cleaned)
            _validate_schema(parsed)
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning("Attempt %s: failed to parse LLM response as JSON: %s", attempt + 1, exc)

    logger.error("LLM response could not be parsed after retry. Raw text: %s", last_raw_text)
    raise ValueError(f"Failed to parse LLM response as valid JSON: {last_error}")


VALID_FAIRNESS_GRADES = {"Even", "Fair", "Slight Edge", "Lopsided", "Unfair"}


def _validate_schema(parsed: dict) -> None:
    if not isinstance(parsed, dict):
        raise ValueError("Response is not a JSON object")
    required_keys = {
        "winner",
        "confidence",
        "marginDescription",
        "players",
        "rationale",
        "fairnessScore",
        "fairnessGrade",
        "fairnessRationale",
    }
    missing = required_keys - parsed.keys()
    if missing:
        raise ValueError(f"Response missing required keys: {missing}")
    if parsed["winner"] not in ("A", "B", "even"):
        raise ValueError(f"Invalid winner value: {parsed['winner']}")
    if not isinstance(parsed["players"], list):
        raise ValueError("players must be a list")
    if not isinstance(parsed["fairnessScore"], (int, float)):
        raise ValueError("fairnessScore must be a number")
    if parsed["fairnessGrade"] not in VALID_FAIRNESS_GRADES:
        raise ValueError(f"Invalid fairnessGrade value: {parsed['fairnessGrade']}")
