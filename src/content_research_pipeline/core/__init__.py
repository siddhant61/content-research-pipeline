"""
Core package for Content Research Pipeline.
"""


def __getattr__(name):
    if name == "ContentResearchPipeline":
        from .pipeline import ContentResearchPipeline
        return ContentResearchPipeline
    if name in ("AnalysisProcessor", "analysis_processor"):
        from .analysis import AnalysisProcessor, analysis_processor
        return {"AnalysisProcessor": AnalysisProcessor, "analysis_processor": analysis_processor}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ContentResearchPipeline",
    "AnalysisProcessor",
    "analysis_processor",
] 