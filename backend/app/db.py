import logging
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

from app import config

logger = logging.getLogger(__name__)

_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
_initialized = False


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        if not config.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to backend/.env (see .env.example)."
            )
        _pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=config.DATABASE_URL)
    return _pool


@contextmanager
def get_cursor(commit: bool = False):
    """Checks out a pooled connection and yields a cursor. Lazily creates the
    schema on first use so the rest of the app (leaderboard, player search)
    keeps working even if Postgres isn't up yet -- only /api/evaluate needs
    the database.
    """
    ensure_schema()
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def ensure_schema() -> None:
    """Idempotent CREATE TABLE IF NOT EXISTS -- fine at this app's scale;
    swap for a real migration tool if the schema grows beyond this."""
    global _initialized
    if _initialized:
        return

    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS verdict_cache (
                    cache_key TEXT PRIMARY KEY,
                    verdict JSONB NOT NULL,
                    week INT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS player_proj_cache (
                    player_id TEXT NOT NULL,
                    week INT NOT NULL,
                    scoring TEXT NOT NULL,
                    adj_projection JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    PRIMARY KEY (player_id, week, scoring)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eval_quota (
                    user_key TEXT NOT NULL,
                    day DATE NOT NULL,
                    count INT NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_key, day)
                )
                """
            )
        conn.commit()
        _initialized = True
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# -- verdict cache -----------------------------------------------------------


def get_cached_verdict(cache_key: str) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT verdict FROM verdict_cache WHERE cache_key = %s", (cache_key,))
        row = cur.fetchone()
        return row["verdict"] if row else None


def store_verdict(cache_key: str, verdict: dict, week: int) -> None:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO verdict_cache (cache_key, verdict, week)
            VALUES (%s, %s, %s)
            ON CONFLICT (cache_key) DO UPDATE SET verdict = EXCLUDED.verdict, week = EXCLUDED.week
            """,
            (cache_key, psycopg2.extras.Json(verdict), week),
        )


# -- per-player projection cache ---------------------------------------------


def get_cached_projection(player_id: str, week: int, scoring: str) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT adj_projection FROM player_proj_cache WHERE player_id = %s AND week = %s AND scoring = %s",
            (player_id, week, scoring),
        )
        row = cur.fetchone()
        return row["adj_projection"] if row else None


def store_projection(player_id: str, week: int, scoring: str, adj_projection: dict) -> None:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO player_proj_cache (player_id, week, scoring, adj_projection)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (player_id, week, scoring)
            DO UPDATE SET adj_projection = EXCLUDED.adj_projection, created_at = now()
            """,
            (player_id, week, scoring, psycopg2.extras.Json(adj_projection)),
        )


# -- daily eval quota (server-key usage only) --------------------------------


def get_quota_count(user_key: str, day) -> int:
    with get_cursor() as cur:
        cur.execute("SELECT count FROM eval_quota WHERE user_key = %s AND day = %s", (user_key, day))
        row = cur.fetchone()
        return row["count"] if row else 0


def increment_quota(user_key: str, day) -> int:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO eval_quota (user_key, day, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_key, day) DO UPDATE SET count = eval_quota.count + 1
            RETURNING count
            """,
            (user_key, day),
        )
        return cur.fetchone()["count"]
