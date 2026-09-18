import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Cost-control knobs -- env-overridable, defaulting to a cheaper tier/lower
# effort/capped search so a dev/test loop doesn't burn API spend. Swap the
# default here (or set the env var) to tune without touching call sites.
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
OPENAI_REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "low")
OPENAI_MAX_TOOL_CALLS = int(os.environ.get("OPENAI_MAX_TOOL_CALLS", "1"))
FREE_EVALS_PER_USER_PER_DAY = int(os.environ.get("FREE_EVALS_PER_USER_PER_DAY", "25"))
INJURED_STATUSES = {"Questionable", "Doubtful", "Out", "IR", "PUP"}
EVAL_RATE_LIMIT = os.environ.get("EVAL_RATE_LIMIT", "10 per minute")

DATABASE_URL = os.environ.get("DATABASE_URL")

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"
SLEEPER_PROJECTIONS_BASE_URL = "https://api.sleeper.app/projections/nfl"
SLEEPER_STATS_BASE_URL = "https://api.sleeper.app/stats/nfl"
SLEEPER_CDN_THUMB_URL = "https://sleepercdn.com/content/nfl/players/thumb"
SLEEPER_TEAM_LOGO_URL = "https://sleepercdn.com/images/team_logos/nfl"

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
PLAYERS_CACHE_FILE = os.path.join(CACHE_DIR, "players.json")
PLAYERS_CACHE_META_FILE = os.path.join(CACHE_DIR, "players_meta.json")
PLAYERS_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60  # fetch player metadata at most once/day

PROJECTIONS_CACHE_MAX_AGE_SECONDS = 60 * 60  # projections refresh hourly

SEASON_STATS_CACHE_MAX_AGE_SECONDS = 60 * 60  # season stats (leaderboard source) refresh hourly
LEADERBOARD_CACHE_MAX_AGE_SECONDS = 60 * 60  # computed leaderboard, refreshed hourly
LEADERBOARD_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
LEADERBOARD_TOP_N = 10

SLEEPER_STATE_URL = "https://api.sleeper.app/v1/state/nfl"
NFL_STATE_CACHE_MAX_AGE_SECONDS = 60 * 60  # current-week lookup, refreshed hourly

SLEEPER_TRENDING_URL = "https://api.sleeper.app/v1/players/nfl/trending/add"
TRENDING_CACHE_MAX_AGE_SECONDS = 60 * 60  # trending-add list, refreshed hourly

# Season/week are approximated from today's date. Override with NFL_SEASON / NFL_WEEK
# env vars if the heuristic is off (e.g. during preseason or offseason testing).
_DEFAULT_SEASON_START = date(date.today().year, 9, 4)


def _current_season() -> int:
    override = os.environ.get("NFL_SEASON")
    if override:
        return int(override)
    today = date.today()
    # NFL season is labeled by the year it starts in (Sept), and runs into the next
    # calendar year, so before September we're still in the prior season.
    return today.year if today.month >= 3 else today.year - 1


def _current_week() -> int:
    override = os.environ.get("NFL_WEEK")
    if override:
        return int(override)
    today = date.today()
    days_since_start = (today - _DEFAULT_SEASON_START).days
    week = (days_since_start // 7) + 1
    return min(18, max(1, week))


CURRENT_SEASON = _current_season()
CURRENT_WEEK = _current_week()

DEFAULT_SCORING = "ppr"
