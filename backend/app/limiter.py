from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Per-IP rate limiting (per-user == per-IP for now, since there's no login
# system). In-memory storage is fine for this single-process dev server;
# swap storage_uri for a shared backend (e.g. Redis) before running multiple
# workers/processes.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
