"""
Generic API key rotator with round-robin rotation.
"""
import threading
import logging

logger = logging.getLogger(__name__)


class KeyRotator:
    """
    Round-robin API key rotator.

    - Cycles through keys on every call to `next()`
    - Thread-safe via a lock
    - Never logs key values, only indices
    """

    def __init__(self, keys: list[str], name: str = ""):
        if not keys:
            raise ValueError(f"{name or 'KeyRotator'}: at least one API key is required")
        self._keys = keys
        self._index = 0
        self._lock = threading.Lock()
        self._name = name or "KeyRotator"
        logger.info(f"{self._name}: initialized with {len(keys)} key(s)")

    @property
    def current_key(self) -> str:
        """Return the key at the current index."""
        with self._lock:
            return self._keys[self._index]

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def next(self) -> str:
        """Advance to the next key (wraps around) and return it."""
        with self._lock:
            old = self._index
            self._index = (self._index + 1) % len(self._keys)
            logger.info(f"{self._name}: rotated key {old} -> {self._index}")
            return self._keys[self._index]
