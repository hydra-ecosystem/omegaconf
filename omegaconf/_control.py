import threading

_syntax_cache_policy = (4 * 1024 * 1024, 0)
_policy_lock = threading.Lock()


class _Control:
    """Process-wide runtime controls for OmegaConf."""

    @staticmethod
    def set_syntax_cache_max_bytes(max_bytes: int) -> None:
        """Set the accounted syntax-cache memory budget for each thread.

        Zero disables syntax caching. Existing threads apply changes on their
        next cache operation; idle threads retain their entries until then or
        until they exit. Operations in progress may use the previous budget.
        This controls parsed syntax, independently of resolver-result caches.
        The budget is not a process RSS limit.

        :param max_bytes: Nonnegative integer budget in bytes per thread.
        :raises TypeError: If ``max_bytes`` is not an integer, or is a boolean.
        :raises ValueError: If ``max_bytes`` is negative.
        """
        if type(max_bytes) is not int:
            raise TypeError("max_bytes must be an integer")
        if max_bytes < 0:
            raise ValueError("max_bytes must be nonnegative")
        global _syntax_cache_policy
        with _policy_lock:
            _syntax_cache_policy = (max_bytes, _syntax_cache_policy[1] + 1)

    @staticmethod
    def get_syntax_cache_max_bytes() -> int:
        """Return the configured syntax-cache budget in bytes per thread.

        This returns the global setting, not current memory usage. Each live
        thread has its own cache and applies updates lazily.
        """
        return _syntax_cache_policy[0]
