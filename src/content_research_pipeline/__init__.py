"""
Content Research Pipeline

Research and enrichment layer of a 3-part AI workflow stack.

Consumes upstream artifacts (RawSourceBundle, NormalizedDocumentSet,
ChunkSet, KnowledgeGraphPackage) and produces a ResearchBrief for
downstream media generation.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"


def __getattr__(name):
    """Lazy import to avoid pulling heavy dependencies at package init."""
    if name == "ContentResearchPipeline":
        from .core.pipeline import ContentResearchPipeline
        return ContentResearchPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ContentResearchPipeline"] 