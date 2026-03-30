"""
Configuration package for Content Research Pipeline.
"""


def __getattr__(name):
    if name == "settings":
        from .settings import settings
        return settings
    if name in ("get_logger", "setup_logging"):
        from .logging import get_logger, setup_logging
        return {"get_logger": get_logger, "setup_logging": setup_logging}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["settings", "get_logger", "setup_logging"] 