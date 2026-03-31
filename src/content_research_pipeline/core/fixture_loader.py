"""
Stable upstream fixture loader for the Content Research Pipeline.

Discovers and loads canonical upstream ingestion artifacts from a fixture
directory (e.g. ``demo_data/jwst_star_formation_early_universe_demo/``).

This module provides a single entry-point for Phase 2A/2B fixture-based
consumption of material-ingestion-pipeline outputs.  It looks for
well-known filenames produced by that pipeline and returns loaded
Pydantic models ready for ``BriefGenerator``.

Well-known filenames
--------------------
* ``KnowledgeGraphPackage.sample.json`` — preferred structured input
* ``NormalizedDocumentSet.sample.json``  — fallback document-level input
* ``ChunkSet.sample.json``              — chunk-level provenance (optional)
* ``manifest.json``                      — RawSourceBundle (source metadata)

Contract assumptions
--------------------
* Fixture JSON files conform to ``contracts/shared_artifacts.json`` v1.0.0.
* ``KnowledgeGraphPackage.provenance`` carries upstream pipeline metadata.
* ``NormalizedDocumentSet.documents[].source_id`` cross-references
  ``RawSourceBundle.sources[].source_id`` for citation enrichment.
* ``ChunkSet.chunks[].source_id`` and ``chunk_id`` may be referenced by KG
  ``SourceRef.chunk_id`` for fine-grained provenance.

Field degradations when KG is consumed without a RawSourceBundle
----------------------------------------------------------------
* ``source_index[].origin_org``  → ``"unknown"``
* ``source_index[].url``         → ``""``
* ``citation_map[].url``         → ``""``
* ``citation_map[].origin_org``  → ``"unknown"``
* ``citation_map[].license``     → ``"unknown"``

These degradations are resolved when a RawSourceBundle (manifest.json) is
also available in the same fixture directory.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data.artifacts import (
    ChunkSet,
    KnowledgeGraphPackage,
    NormalizedDocumentSet,
    RawSourceBundle,
)


# Well-known filenames emitted by material-ingestion-pipeline
_KG_FILENAMES = [
    "KnowledgeGraphPackage.sample.json",
    "KnowledgeGraphPackage.json",
]
_NDS_FILENAMES = [
    "NormalizedDocumentSet.sample.json",
    "NormalizedDocumentSet.json",
]
_CHUNK_FILENAMES = [
    "ChunkSet.sample.json",
    "ChunkSet.json",
]
_BUNDLE_FILENAMES = [
    "manifest.json",
    "RawSourceBundle.json",
    "RawSourceBundle.sample.json",
]


def _find_first(directory: Path, candidates: List[str]) -> Optional[Path]:
    """Return the first candidate file that exists in *directory*."""
    for name in candidates:
        p = directory / name
        if p.is_file():
            return p
    return None


@dataclass
class UpstreamFixtures:
    """Container for upstream fixture artifacts discovered in a directory.

    Attributes:
        fixture_dir: Path to the fixture directory that was scanned.
        graph: Loaded KnowledgeGraphPackage, if found.
        documents: Loaded NormalizedDocumentSet, if found.
        chunks: Loaded ChunkSet, if found.
        bundle: Loaded RawSourceBundle (manifest), if found.
        graph_path: Path to the KG fixture file, if found.
        documents_path: Path to the NDS fixture file, if found.
        chunks_path: Path to the ChunkSet fixture file, if found.
        bundle_path: Path to the manifest fixture file, if found.
        warnings: Human-readable notes about missing or degraded data.
    """
    fixture_dir: str
    graph: Optional[KnowledgeGraphPackage] = None
    documents: Optional[NormalizedDocumentSet] = None
    chunks: Optional[ChunkSet] = None
    bundle: Optional[RawSourceBundle] = None
    graph_path: Optional[str] = None
    documents_path: Optional[str] = None
    chunks_path: Optional[str] = None
    bundle_path: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def has_any(self) -> bool:
        """True if at least one upstream artifact was loaded."""
        return (
            self.graph is not None
            or self.documents is not None
            or self.chunks is not None
            or self.bundle is not None
        )

    @property
    def summary(self) -> Dict[str, Any]:
        """Return a short summary dict suitable for logging / RunManifest."""
        return {
            "fixture_dir": self.fixture_dir,
            "graph_loaded": self.graph is not None,
            "documents_loaded": self.documents is not None,
            "chunks_loaded": self.chunks is not None,
            "bundle_loaded": self.bundle is not None,
            "graph_path": self.graph_path,
            "documents_path": self.documents_path,
            "chunks_path": self.chunks_path,
            "bundle_path": self.bundle_path,
            "warnings": self.warnings,
        }


def load_upstream_fixtures(fixture_dir: str) -> UpstreamFixtures:
    """Discover and load canonical upstream fixture artifacts.

    Scans *fixture_dir* for well-known filenames and loads every artifact
    that is found.  Returns an ``UpstreamFixtures`` container with all
    loaded artifacts and any warnings about missing or degraded data.

    Args:
        fixture_dir: Path to the fixture directory to scan.

    Returns:
        An ``UpstreamFixtures`` with all discovered artifacts loaded.

    Raises:
        FileNotFoundError: If *fixture_dir* does not exist.
    """
    d = Path(fixture_dir)
    if not d.is_dir():
        raise FileNotFoundError(f"Fixture directory not found: {fixture_dir}")

    result = UpstreamFixtures(fixture_dir=str(d))

    # ── KnowledgeGraphPackage ────────────────────────────────────────
    kg_path = _find_first(d, _KG_FILENAMES)
    if kg_path:
        with open(kg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result.graph = KnowledgeGraphPackage(**data)
        result.graph_path = str(kg_path)
    else:
        result.warnings.append(
            "No KnowledgeGraphPackage found — brief will use NDS or bundle fallback."
        )

    # ── NormalizedDocumentSet ────────────────────────────────────────
    nds_path = _find_first(d, _NDS_FILENAMES)
    if nds_path:
        with open(nds_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result.documents = NormalizedDocumentSet(**data)
        result.documents_path = str(nds_path)
    else:
        result.warnings.append(
            "No NormalizedDocumentSet found — brief will use KG or bundle fallback."
        )

    # ── ChunkSet ─────────────────────────────────────────────────────
    chunk_path = _find_first(d, _CHUNK_FILENAMES)
    if chunk_path:
        with open(chunk_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result.chunks = ChunkSet(**data)
        result.chunks_path = str(chunk_path)
    else:
        result.warnings.append(
            "No ChunkSet found — chunk-level provenance unavailable."
        )

    # ── RawSourceBundle (manifest) ───────────────────────────────────
    bundle_path = _find_first(d, _BUNDLE_FILENAMES)
    if bundle_path:
        with open(bundle_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result.bundle = RawSourceBundle(**data)
        result.bundle_path = str(bundle_path)
    else:
        result.warnings.append(
            "No RawSourceBundle (manifest) found — source attribution will be degraded."
        )

    # ── Cross-reference warnings ─────────────────────────────────────
    if result.graph and not result.bundle:
        result.warnings.append(
            "KG loaded without manifest: source_index origin_org/url will be 'unknown'/''."
        )

    if not result.has_any:
        result.warnings.append(
            "No upstream fixtures found in directory — cannot generate a ResearchBrief."
        )

    return result
