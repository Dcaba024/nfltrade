import base64
import io
import json
import logging

from openai import OpenAI
from PIL import Image, UnidentifiedImageError

from app import config
from app.llm.evaluator import _extract_output_text, _strip_markdown_fences

logger = logging.getLogger(__name__)

# Longest edge the screenshot is scaled down to before upload. Roster text
# stays legible well below this, and vision input cost scales with pixels.
MAX_IMAGE_EDGE = 1600
MAX_ROSTER_ENTRIES = 30
VALID_SLOTS = {"starter", "bench", "ir"}

ROSTER_PROMPT = """Read this fantasy football roster screenshot. List every NFL player and team defense on the roster exactly as shown.
- slot: "starter" (in a starting lineup slot incl. FLEX/SUPERFLEX), "bench", or "ir" (IR/injured reserve slot).
- position: QB|RB|WR|TE|K|DEF (team defenses / D/ST are DEF; use the player's real position for FLEX slots).
- team: NFL team abbreviation if visible, else null.
- Ignore empty slots, opponents, scores, and anything that isn't a rostered player.
- Not a fantasy roster -> "players": [].
Output ONLY this JSON, no markdown fences:
{"players":[{"name":"","position":"","team":null,"slot":"starter"}]}"""


def prepare_image(raw: bytes) -> tuple[bytes, str]:
    """Decodes the upload with Pillow (rejecting anything that isn't really
    an image), downscales it, and re-encodes as PNG -- the model only ever
    sees pixels we produced, never the client's original bytes."""
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Upload is not a readable image") from exc

    image = image.convert("RGB")
    image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue(), "image/png"


def extract_roster(image_bytes: bytes, mime: str, api_key: str) -> list[dict]:
    """One vision call: screenshot -> raw roster entries (names as written
    on screen). Matching to real players happens afterwards, against Sleeper
    data, so the model never decides who a player "is"."""
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    client = OpenAI(api_key=api_key)

    last_error = None
    for attempt in range(2):
        response = client.responses.create(
            model=config.OPENAI_MODEL,
            reasoning={"effort": config.OPENAI_REASONING_EFFORT},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": ROSTER_PROMPT},
                        {"type": "input_image", "image_url": data_url, "detail": "high"},
                    ],
                }
            ],
        )
        try:
            parsed = json.loads(_strip_markdown_fences(_extract_output_text(response)))
            return _validate_entries(parsed)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning("Attempt %s: failed to parse roster extraction: %s", attempt + 1, exc)

    raise ValueError(f"Could not read a roster from that image: {last_error}")


def _validate_entries(parsed) -> list[dict]:
    if not isinstance(parsed, dict) or not isinstance(parsed.get("players"), list):
        raise ValueError("Response missing 'players' list")
    entries = []
    for item in parsed["players"][:MAX_ROSTER_ENTRIES]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 60:
            continue
        position = item.get("position") if isinstance(item.get("position"), str) else None
        team = item.get("team") if isinstance(item.get("team"), str) and len(item["team"]) <= 5 else None
        slot = item.get("slot") if item.get("slot") in VALID_SLOTS else "bench"
        entries.append({"name": name.strip(), "position": position, "team": team, "slot": slot})
    return entries
