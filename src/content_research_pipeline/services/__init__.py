"""
Services package for Content Research Pipeline.
"""

_service_map = {
    "search_service": (".search", "search_service"),
    "SearchService": (".search", "SearchService"),
    "scraper_service": (".scraper", "scraper_service"),
    "ScraperService": (".scraper", "ScraperService"),
    "vector_store_service": (".vector_store", "vector_store_service"),
    "VectorStoreService": (".vector_store", "VectorStoreService"),
    "llm_service": (".llm", "llm_service"),
    "LLMService": (".llm", "LLMService"),
}


def __getattr__(name):
    if name in _service_map:
        mod_path, attr = _service_map[name]
        import importlib
        mod = importlib.import_module(mod_path, __name__)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_service_map.keys()) 