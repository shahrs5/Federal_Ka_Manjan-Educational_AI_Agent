"""
Groq API client with automatic key rotation on rate-limit (429).

Drop-in replacement: agents use `client.chat.completions.create(...)` unchanged.
"""
import time
import logging
from groq import Groq, RateLimitError
from .key_rotator import KeyRotator
from ..config import settings

logger = logging.getLogger(__name__)


class _CompletionsProxy:
    """Proxies `chat.completions.create()` with key rotation."""

    def __init__(self, rotator: KeyRotator, max_retries: int = 10):
        self._rotator = rotator
        self._clients: dict[str, Groq] = {}
        self._max_retries = max_retries

    def _get_client(self, key: str) -> Groq:
        if key not in self._clients:
            self._clients[key] = Groq(api_key=key)
        return self._clients[key]

    def create(self, **kwargs):
        """Call Groq chat completions with automatic key rotation on 429."""
        keys_tried = 0
        total_keys = self._rotator.key_count

        for attempt in range(self._max_retries):
            client = self._get_client(self._rotator.current_key)
            try:
                return client.chat.completions.create(**kwargs)
            except RateLimitError:
                keys_tried += 1
                self._rotator.next()

                if keys_tried >= total_keys:
                    # All keys exhausted in this round — backoff
                    wait = min(2 ** (attempt - total_keys + 1), 60)
                    logger.warning(
                        f"All {total_keys} Groq keys rate-limited, "
                        f"backing off {wait}s (attempt {attempt + 1})"
                    )
                    time.sleep(wait)
                    keys_tried = 0

        raise RateLimitError(
            f"All Groq keys exhausted after {self._max_retries} attempts",
            response=None,
            body=None,
        )


class _ChatProxy:
    """Proxies `chat.completions`."""

    def __init__(self, completions: _CompletionsProxy):
        self.completions = completions


class RotatingGroqClient:
    """
    Drop-in replacement for `Groq` that rotates API keys.

    Usage is identical: `client.chat.completions.create(model=..., messages=...)`
    """

    def __init__(self, keys: list[str]):
        rotator = KeyRotator(keys, name="Groq")
        self.chat = _ChatProxy(_CompletionsProxy(rotator))


def get_groq_client() -> RotatingGroqClient:
    """Get a rotating Groq client using all configured keys."""
    return RotatingGroqClient(settings.groq_key_list)
