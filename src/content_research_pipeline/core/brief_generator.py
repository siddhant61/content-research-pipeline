"""
Brief generator for the Content Research Pipeline.

Reads upstream artifacts (RawSourceBundle, NormalizedDocumentSet, ChunkSet,
KnowledgeGraphPackage) and synthesizes a ResearchBrief that conforms to the
shared artifact contract.

Phase 1.5 implementation: generates a structured brief from upstream ingestion
artifacts with the following input priority:
    1. KnowledgeGraphPackage (preferred — richest structured input)
    2. NormalizedDocumentSet (fallback — document-level content)
    3. RawSourceBundle / manifest (fallback — source metadata only)

No LLM or live web search is required.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data.artifacts import (
    ChunkSet,
    KeyFinding,
    KnowledgeGraphPackage,
    NormalizedDocumentSet,
    RawSourceBundle,
    ResearchBrief,
    RunManifest,
    SourceIndexEntry,
    TimelineEntry,
)


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_id(prefix: str = "res") -> str:
    """Generate a short unique id."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── Loaders ──────────────────────────────────────────────────────────────────

def load_raw_source_bundle(path: str) -> RawSourceBundle:
    """Load a RawSourceBundle JSON file (e.g. the demo manifest)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return RawSourceBundle(**data)


def load_normalized_document_set(path: str) -> NormalizedDocumentSet:
    """Load a NormalizedDocumentSet JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return NormalizedDocumentSet(**data)


def load_chunk_set(path: str) -> ChunkSet:
    """Load a ChunkSet JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ChunkSet(**data)


def load_knowledge_graph(path: str) -> KnowledgeGraphPackage:
    """Load a KnowledgeGraphPackage JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return KnowledgeGraphPackage(**data)


# ── Source index builders ────────────────────────────────────────────────────

def _build_source_index(bundle: RawSourceBundle) -> List[SourceIndexEntry]:
    """Build source_index from a RawSourceBundle."""
    entries: List[SourceIndexEntry] = []
    for src in bundle.sources:
        entries.append(
            SourceIndexEntry(
                source_id=src.source_id,
                title=src.title,
                origin_org=src.origin_org,
                url=src.url,
                source_type=src.source_type,
                credibility_notes=src.usage_notes,
            )
        )
    return entries


def _build_source_index_from_graph(
    graph: KnowledgeGraphPackage,
) -> List[SourceIndexEntry]:
    """Build source_index from KnowledgeGraphPackage source_refs.

    Collects unique source_ids referenced across all graph nodes and edges,
    creating a minimal SourceIndexEntry for each.
    """
    seen: Dict[str, SourceIndexEntry] = {}
    for node in graph.nodes:
        for ref in node.source_refs:
            if ref.source_id not in seen:
                seen[ref.source_id] = SourceIndexEntry(
                    source_id=ref.source_id,
                    title=ref.source_id,
                    origin_org="unknown",
                    url="",
                    source_type="graph-reference",
                    credibility_notes=f"Referenced by graph node '{node.label}'",
                )
    for edge in graph.edges:
        for ref in edge.source_refs:
            if ref.source_id not in seen:
                seen[ref.source_id] = SourceIndexEntry(
                    source_id=ref.source_id,
                    title=ref.source_id,
                    origin_org="unknown",
                    url="",
                    source_type="graph-reference",
                    credibility_notes=f"Referenced by graph edge '{edge.relation_type}'",
                )
    return list(seen.values())


def _build_source_index_from_documents(
    docs: NormalizedDocumentSet,
) -> List[SourceIndexEntry]:
    """Build source_index from NormalizedDocumentSet."""
    seen: Dict[str, SourceIndexEntry] = {}
    for doc in docs.documents:
        if doc.source_id not in seen:
            seen[doc.source_id] = SourceIndexEntry(
                source_id=doc.source_id,
                title=doc.title,
                origin_org="unknown",
                url="",
                source_type=doc.document_type,
                credibility_notes=f"Normalized document: {doc.title}",
            )
    return list(seen.values())


# ── Citation map builders ────────────────────────────────────────────────────

def _build_citation_map(bundle: RawSourceBundle) -> Dict[str, Any]:
    """Build citation_map keyed by source_id."""
    cmap: Dict[str, Any] = {}
    for src in bundle.sources:
        cmap[src.source_id] = {
            "title": src.title,
            "url": src.url,
            "origin_org": src.origin_org,
            "license": src.license,
        }
    return cmap


def _build_citation_map_from_graph(
    graph: KnowledgeGraphPackage,
) -> Dict[str, Any]:
    """Build citation_map from KnowledgeGraphPackage source_refs."""
    cmap: Dict[str, Any] = {}
    for node in graph.nodes:
        for ref in node.source_refs:
            if ref.source_id not in cmap:
                cmap[ref.source_id] = {
                    "title": ref.source_id,
                    "url": "",
                    "origin_org": "unknown",
                    "license": "unknown",
                }
    for edge in graph.edges:
        for ref in edge.source_refs:
            if ref.source_id not in cmap:
                cmap[ref.source_id] = {
                    "title": ref.source_id,
                    "url": "",
                    "origin_org": "unknown",
                    "license": "unknown",
                }
    return cmap


def _build_citation_map_from_documents(
    docs: NormalizedDocumentSet,
) -> Dict[str, Any]:
    """Build citation_map from NormalizedDocumentSet."""
    cmap: Dict[str, Any] = {}
    for doc in docs.documents:
        if doc.source_id not in cmap:
            cmap[doc.source_id] = {
                "title": doc.title,
                "url": "",
                "origin_org": "unknown",
                "license": "unknown",
            }
    return cmap


# ── Entity builders ──────────────────────────────────────────────────────────

def _build_entities_from_seeds(
    seed_entities: List[str],
    source_ids: List[str],
) -> List[Dict[str, Any]]:
    """Build entity list from seed entities.

    Note: ``seed_entities`` is an *internal extension* of the RawSourceBundle —
    it is NOT part of the formal shared contract (contracts/shared_artifacts.json).
    It is used here only as a convenience when no richer upstream artifact is
    available.
    """
    entities: List[Dict[str, Any]] = []
    for label in seed_entities:
        entities.append(
            {
                "entity_id": _make_id("ent"),
                "label": label,
                "entity_type": "seed",
                "source_refs": source_ids[:2],
            }
        )
    return entities


def _build_entities_from_graph(
    graph: KnowledgeGraphPackage,
) -> List[Dict[str, Any]]:
    """Build entity list from a KnowledgeGraphPackage."""
    entities: List[Dict[str, Any]] = []
    for node in graph.nodes:
        entities.append(
            {
                "entity_id": node.node_id,
                "label": node.label,
                "entity_type": node.node_type,
                "description": node.description,
                "aliases": node.aliases,
                "source_refs": [
                    ref.source_id for ref in node.source_refs
                ],
            }
        )
    return entities


def _build_entities_from_documents(
    docs: NormalizedDocumentSet,
) -> List[Dict[str, Any]]:
    """Build minimal entity list from NormalizedDocumentSet.

    Without a knowledge graph, documents are treated as entity-like objects
    so that the entities field is non-empty for downstream consumers.
    """
    entities: List[Dict[str, Any]] = []
    for doc in docs.documents:
        entities.append(
            {
                "entity_id": _make_id("ent"),
                "label": doc.title,
                "entity_type": "document-topic",
                "source_refs": [doc.source_id],
            }
        )
    return entities


# ── Finding builders ─────────────────────────────────────────────────────────

def _build_placeholder_findings(
    topic: str,
    seed_entities: List[str],
) -> List[KeyFinding]:
    """Generate placeholder key findings from seed entities."""
    findings: List[KeyFinding] = []
    if seed_entities:
        findings.append(
            KeyFinding(
                finding_id=_make_id("find"),
                claim=f"The topic '{topic}' involves {len(seed_entities)} key entities: {', '.join(seed_entities[:5])}.",
                importance="high",
                confidence=0.6,
                evidence_refs=[],
            )
        )
    return findings


def _build_findings_from_documents(
    docs: NormalizedDocumentSet,
) -> List[KeyFinding]:
    """Extract findings from normalized documents."""
    findings: List[KeyFinding] = []
    for doc in docs.documents:
        if doc.text:
            preview = doc.text[:200].strip()
            findings.append(
                KeyFinding(
                    finding_id=_make_id("find"),
                    claim=f"Source '{doc.title}' states: {preview}",
                    importance="medium",
                    confidence=0.5,
                    evidence_refs=[doc.source_id],
                )
            )
    return findings


def _build_findings_from_graph(
    graph: KnowledgeGraphPackage,
) -> List[KeyFinding]:
    """Extract findings from KnowledgeGraphPackage edges and nodes.

    Each edge becomes a finding whose claim describes the relationship.
    Node descriptions are used as supplementary findings.
    """
    findings: List[KeyFinding] = []
    node_map = {n.node_id: n.label for n in graph.nodes}

    for edge in graph.edges:
        src_label = node_map.get(edge.source_node_id, edge.source_node_id)
        tgt_label = node_map.get(edge.target_node_id, edge.target_node_id)
        evidence = [ref.source_id for ref in edge.source_refs]
        findings.append(
            KeyFinding(
                finding_id=_make_id("find"),
                claim=f"{src_label} {edge.relation_type} {tgt_label}",
                importance="high",
                confidence=edge.weight,
                evidence_refs=evidence,
            )
        )

    for node in graph.nodes:
        if node.description:
            findings.append(
                KeyFinding(
                    finding_id=_make_id("find"),
                    claim=f"{node.label}: {node.description}",
                    importance="medium",
                    confidence=0.7,
                    evidence_refs=[ref.source_id for ref in node.source_refs],
                )
            )

    return findings


# ── Brief generator ──────────────────────────────────────────────────────────

class BriefGenerator:
    """
    Generates a contract-compliant ResearchBrief from upstream artifacts.

    Input priority (Phase 1.5):
        1. KnowledgeGraphPackage — richest structured input; entities and
           findings are derived from graph nodes and edges.
        2. NormalizedDocumentSet — document-level content; findings extracted
           from document text.
        3. RawSourceBundle (manifest) — source metadata only; produces
           placeholder findings from seed entities.

    At least one of ``bundle``, ``documents``, or ``graph`` must be provided.
    """

    def __init__(
        self,
        bundle: Optional[RawSourceBundle] = None,
        documents: Optional[NormalizedDocumentSet] = None,
        chunks: Optional[ChunkSet] = None,
        graph: Optional[KnowledgeGraphPackage] = None,
    ):
        if bundle is None and documents is None and graph is None:
            raise ValueError(
                "At least one of bundle, documents, or graph must be provided."
            )
        self.bundle = bundle
        self.documents = documents
        self.chunks = chunks
        self.graph = graph

    # ── Topic resolution ─────────────────────────────────────────────────

    def _resolve_topic(self) -> str:
        """Resolve topic from the highest-priority artifact."""
        if self.graph:
            return self.graph.topic
        if self.documents:
            return self.documents.topic
        assert self.bundle is not None  # guaranteed by __init__
        return self.bundle.topic

    # ── Source attribution ───────────────────────────────────────────────

    def _resolve_source_index(self) -> List[SourceIndexEntry]:
        """Build source_index using all available artifacts.

        Merges source information from bundle, documents, and graph,
        preferring the richest available data per source_id.
        """
        entries: Dict[str, SourceIndexEntry] = {}

        # Start with bundle sources (most complete per-source metadata)
        if self.bundle:
            for entry in _build_source_index(self.bundle):
                entries[entry.source_id] = entry

        # Merge document sources (may add new source_ids)
        if self.documents:
            for entry in _build_source_index_from_documents(self.documents):
                if entry.source_id not in entries:
                    entries[entry.source_id] = entry

        # Merge graph source_refs (may add new source_ids)
        if self.graph:
            for entry in _build_source_index_from_graph(self.graph):
                if entry.source_id not in entries:
                    entries[entry.source_id] = entry

        return list(entries.values())

    def _resolve_citation_map(self) -> Dict[str, Any]:
        """Build citation_map using all available artifacts.

        Merges citation info from bundle, documents, and graph,
        preferring the richest available data per source_id.
        """
        cmap: Dict[str, Any] = {}

        # Start with bundle citations (most complete)
        if self.bundle:
            cmap.update(_build_citation_map(self.bundle))

        # Merge document citations
        if self.documents:
            for sid, val in _build_citation_map_from_documents(self.documents).items():
                if sid not in cmap:
                    cmap[sid] = val

        # Merge graph citations
        if self.graph:
            for sid, val in _build_citation_map_from_graph(self.graph).items():
                if sid not in cmap:
                    cmap[sid] = val

        return cmap

    # ── Entity resolution ────────────────────────────────────────────────

    def _resolve_entities(self) -> List[Dict[str, Any]]:
        """Build entities using the highest-priority source.

        Priority: graph nodes > document topics > seed entities.
        """
        if self.graph and self.graph.nodes:
            return _build_entities_from_graph(self.graph)

        if self.documents and self.documents.documents:
            return _build_entities_from_documents(self.documents)

        if self.bundle:
            # seed_entities is an internal extension, not a formal contract field
            seed_entities = self.bundle.seed_entities or []
            source_ids = [s.source_id for s in self.bundle.sources]
            return _build_entities_from_seeds(seed_entities, source_ids)

        return []

    # ── Finding resolution ───────────────────────────────────────────────

    def _resolve_findings(self, topic: str) -> List[KeyFinding]:
        """Build key findings using the highest-priority source.

        Priority: graph edges/nodes > document text > seed placeholders.
        """
        if self.graph and (self.graph.nodes or self.graph.edges):
            findings = _build_findings_from_graph(self.graph)
            if findings:
                return findings

        if self.documents and self.documents.documents:
            findings = _build_findings_from_documents(self.documents)
            if findings:
                return findings

        seed_entities = (self.bundle.seed_entities or []) if self.bundle else []
        return _build_placeholder_findings(topic, seed_entities)

    # ── Main generation ──────────────────────────────────────────────────

    def generate(
        self,
        research_question: Optional[str] = None,
    ) -> ResearchBrief:
        """
        Generate a ResearchBrief from the loaded artifacts.

        Args:
            research_question: Override the default research question.

        Returns:
            A valid ResearchBrief matching the shared contract.
        """
        topic = self._resolve_topic()

        # Default research question from topic
        if not research_question:
            research_question = f"What are the key aspects of: {topic}?"

        # Build source attribution
        source_index = self._resolve_source_index()
        citation_map = self._resolve_citation_map()

        # Build entities
        entities = self._resolve_entities()

        # Build key findings
        findings = self._resolve_findings(topic)

        # Build executive summary
        entity_labels = [e.get("label", "") for e in entities[:5]]
        entity_names = ", ".join(entity_labels) if entity_labels else "the topic"
        source_count = len(source_index)
        executive_summary = (
            f"This research brief covers '{topic}' based on {source_count} "
            f"curated source(s). Key entities include {entity_names}. "
            f"The brief synthesizes available information to address: "
            f"{research_question}"
        )

        # Build timeline (placeholder unless graph provides events)
        timeline: List[TimelineEntry] = []

        # Open questions
        open_questions = [
            f"What additional sources are needed to deepen coverage of {topic}?",
            "Are there recent developments not yet captured in the source bundle?",
        ]

        # Recommended angles
        first_entity = entity_labels[0] if entity_labels else None
        recommended_angles = [
            f"Deep dive into {first_entity}" if first_entity else "Broad topic overview",
            "Source credibility comparison across organizations",
            "Timeline of key milestones and discoveries",
        ]

        run_id = _make_id("run")

        brief = ResearchBrief(
            artifact_id=_make_id("brief"),
            created_at=_now_iso(),
            producer="content-research-pipeline",
            source_run_id=run_id,
            topic=topic,
            research_question=research_question,
            executive_summary=executive_summary,
            key_findings=findings,
            entities=entities,
            timeline=timeline,
            source_index=source_index,
            citation_map=citation_map,
            open_questions=open_questions,
            recommended_angles=recommended_angles,
        )

        return brief

    def generate_run_manifest(
        self,
        brief: ResearchBrief,
        output_path: Optional[str] = None,
    ) -> RunManifest:
        """
        Generate a RunManifest tracking this research run.

        Args:
            brief: The ResearchBrief that was produced.
            output_path: Path where the brief was written (if any).

        Returns:
            A RunManifest artifact.
        """
        outputs = []
        if output_path:
            outputs.append(output_path)

        source_count = 0
        if self.bundle:
            source_count = len(self.bundle.sources)
        elif self.documents:
            source_count = len(self.documents.documents)
        elif self.graph:
            source_count = len(self.graph.nodes)

        return RunManifest(
            artifact_id=_make_id("manifest"),
            created_at=_now_iso(),
            producer="content-research-pipeline",
            source_run_id=brief.source_run_id,
            pipeline_stage="generate-brief",
            status="completed",
            inputs={
                "raw_source_bundle": self.bundle.artifact_id if self.bundle else None,
                "documents": self.documents.artifact_id if self.documents else None,
                "chunks": self.chunks.artifact_id if self.chunks else None,
                "graph": self.graph.artifact_id if self.graph else None,
            },
            outputs=outputs,
            metrics={
                "source_count": source_count,
                "finding_count": len(brief.key_findings),
                "entity_count": len(brief.entities),
            },
            errors=[],
        )


# ── Convenience functions ────────────────────────────────────────────────────

def _resolve_topic_slug(
    bundle: Optional[RawSourceBundle] = None,
    documents: Optional[NormalizedDocumentSet] = None,
    graph: Optional[KnowledgeGraphPackage] = None,
) -> str:
    """Resolve a filesystem-safe topic slug from available artifacts."""
    if bundle and bundle.source_bundle_name:
        return bundle.source_bundle_name
    topic = ""
    if graph:
        topic = graph.topic
    elif documents:
        topic = documents.topic
    elif bundle:
        topic = bundle.topic
    return topic.replace(" ", "_").lower()[:80] or "research"


def generate_brief_from_manifest(
    manifest_path: str,
    research_question: Optional[str] = None,
    documents_path: Optional[str] = None,
    chunks_path: Optional[str] = None,
    graph_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    End-to-end convenience function: load manifest, generate brief, write output.

    Args:
        manifest_path: Path to the RawSourceBundle JSON (e.g. demo manifest.json).
        research_question: Optional override for the research question.
        documents_path: Optional path to a NormalizedDocumentSet JSON.
        chunks_path: Optional path to a ChunkSet JSON.
        graph_path: Optional path to a KnowledgeGraphPackage JSON.
        output_dir: Directory to write output files. Defaults to current directory.

    Returns:
        Dict with keys 'brief', 'run_manifest', 'brief_path', 'manifest_path'.
    """
    bundle = load_raw_source_bundle(manifest_path)

    documents = load_normalized_document_set(documents_path) if documents_path else None
    chunks = load_chunk_set(chunks_path) if chunks_path else None
    graph = load_knowledge_graph(graph_path) if graph_path else None

    generator = BriefGenerator(
        bundle=bundle,
        documents=documents,
        chunks=chunks,
        graph=graph,
    )

    brief = generator.generate(research_question=research_question)

    # Determine output paths
    out = Path(output_dir) if output_dir else Path(".")
    out.mkdir(parents=True, exist_ok=True)

    topic_slug = _resolve_topic_slug(bundle, documents, graph)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

    brief_filename = f"{topic_slug}__ResearchBrief__{ts}.json"
    manifest_filename = f"{topic_slug}__RunManifest__{ts}.json"

    brief_path = out / brief_filename
    manifest_path_out = out / manifest_filename

    brief_path.write_text(
        brief.model_dump_json(indent=2), encoding="utf-8"
    )
    run_manifest_out = generator.generate_run_manifest(brief, str(brief_path))
    manifest_path_out.write_text(
        run_manifest_out.model_dump_json(indent=2), encoding="utf-8"
    )

    return {
        "brief": brief,
        "run_manifest": run_manifest_out,
        "brief_path": str(brief_path),
        "manifest_path": str(manifest_path_out),
    }


def generate_brief_from_artifacts(
    research_question: Optional[str] = None,
    manifest_path: Optional[str] = None,
    documents_path: Optional[str] = None,
    chunks_path: Optional[str] = None,
    graph_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    End-to-end convenience function with flexible input priority.

    Accepts any combination of upstream artifacts.  At least one of
    ``manifest_path``, ``documents_path``, or ``graph_path`` must be provided.

    Input priority for content synthesis:
        1. KnowledgeGraphPackage (richest structured input)
        2. NormalizedDocumentSet (document-level content)
        3. RawSourceBundle / manifest (source metadata only)

    Args:
        research_question: Optional override for the research question.
        manifest_path: Optional path to a RawSourceBundle JSON.
        documents_path: Optional path to a NormalizedDocumentSet JSON.
        chunks_path: Optional path to a ChunkSet JSON.
        graph_path: Optional path to a KnowledgeGraphPackage JSON.
        output_dir: Directory to write output files.  Defaults to current directory.

    Returns:
        Dict with keys 'brief', 'run_manifest', 'brief_path', 'manifest_path'.

    Raises:
        ValueError: If none of manifest_path, documents_path, or graph_path is given.
    """
    if not manifest_path and not documents_path and not graph_path:
        raise ValueError(
            "At least one of manifest_path, documents_path, or graph_path "
            "must be provided."
        )

    bundle = load_raw_source_bundle(manifest_path) if manifest_path else None
    documents = load_normalized_document_set(documents_path) if documents_path else None
    chunks = load_chunk_set(chunks_path) if chunks_path else None
    graph = load_knowledge_graph(graph_path) if graph_path else None

    generator = BriefGenerator(
        bundle=bundle,
        documents=documents,
        chunks=chunks,
        graph=graph,
    )

    brief = generator.generate(research_question=research_question)

    # Determine output paths
    out = Path(output_dir) if output_dir else Path(".")
    out.mkdir(parents=True, exist_ok=True)

    topic_slug = _resolve_topic_slug(bundle, documents, graph)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

    brief_filename = f"{topic_slug}__ResearchBrief__{ts}.json"
    manifest_filename = f"{topic_slug}__RunManifest__{ts}.json"

    brief_path = out / brief_filename
    manifest_path_out = out / manifest_filename

    brief_path.write_text(
        brief.model_dump_json(indent=2), encoding="utf-8"
    )
    run_manifest_out = generator.generate_run_manifest(brief, str(brief_path))
    manifest_path_out.write_text(
        run_manifest_out.model_dump_json(indent=2), encoding="utf-8"
    )

    return {
        "brief": brief,
        "run_manifest": run_manifest_out,
        "brief_path": str(brief_path),
        "manifest_path": str(manifest_path_out),
    }
