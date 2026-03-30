"""
Utilities package for Content Research Pipeline.
"""


def __getattr__(name):
    _caching_names = {"cache_result", "cache_sync_result", "cache_manager", "clear_cache"}
    if name in _caching_names:
        import importlib
        mod = importlib.import_module(".caching", __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["cache_result", "cache_sync_result", "cache_manager", "clear_cache"] 