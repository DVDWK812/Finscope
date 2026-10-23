"""Persist provider cooldowns locally; never retry or sleep through a 429."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import tempfile


COOLDOWN_PATH = Path(__file__).resolve().parents[1] / "reports" / "provider_cooldowns.json"


def safe_retry_after(value: str) -> str | None:
    """Accept delay-seconds or an HTTP date; never return arbitrary header text."""
    if re.fullmatch(r"[0-9]+", value):
        return value
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is not None:
            return format_datetime(parsed.astimezone(timezone.utc), usegmt=True)
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def retry_deadline(value: str | None, now: datetime) -> datetime:
    """Missing/invalid Retry-After on a 429 means our conservative 24h hold."""
    safe = safe_retry_after(value) if value else None
    if safe and re.fullmatch(r"[0-9]+", safe):
        try:
            if len(safe) > 12:
                return datetime.max.replace(tzinfo=timezone.utc)
            return now + timedelta(seconds=int(safe))
        except OverflowError:
            return datetime.max.replace(tzinfo=timezone.utc)
    if safe:
        return parsedate_to_datetime(safe).astimezone(timezone.utc)
    return now + timedelta(hours=24)


def load_cooldowns(path: Path) -> dict[str, datetime]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError
        result = {}
        for provider, value in data.items():
            if provider not in ("gdelt", "marketaux", "newsdata", "finnhub") or not isinstance(value, str):
                raise ValueError
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                raise ValueError
            result[provider] = parsed.astimezone(timezone.utc)
        return result
    except (ValueError, TypeError, OverflowError):
        # Do not silently discard a broken hold and issue a fresh request.
        raise ValueError("Invalid local cooldown state; no requests allowed until reviewed") from None


def save_cooldowns(path: Path, cooldowns: dict[str, datetime]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="cooldown_", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({key: value.isoformat() for key, value in cooldowns.items()}, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
