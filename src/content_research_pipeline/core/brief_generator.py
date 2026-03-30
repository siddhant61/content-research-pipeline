"""
Brief generator for the Content Research Pipeline.

Reads upstream artifacts (RawSourceBundle, NormalizedDocumentSet, ChunkSet,
KnowledgeGraphPackage) and synthesizes a ResearchBrief that conforms to the
shared artifact contract.

Phase 1 implementation: generates a structured brief from manifest metadata
and seed entities without requiring an LLM or live web search.
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


# ── Source index builder ─────────────────────────────────────────────────────

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


# ── Citation map builder ─────────────────────────────────────────────────────

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


# ── Entity builder ───────────────────────────────────────────────────────────

def _build_entities_from_seeds(
    seed_entities: List[str],
    bundle: RawSourceBundle,
) -> List[Dict[str, Any]]:
    """Build entity list from seed entities in the manifest."""
    entities: List[Dict[str, Any]] = []
    source_ids = [s.source_id for s in bundle.sources]
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


# ── Finding builder ──────────────────────────────────────────────────────────

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


# ── Brief generator ──────────────────────────────────────────────────────────

class BriefGenerator:
    """
    Generates a contract-compliant ResearchBrief from upstream artifacts.

    Phase 1 happy path:
        1. Load the demo manifest (RawSourceBundle).
        2. Optionally load NormalizedDocumentSet, ChunkSet, KnowledgeGraphPackage.
        3. Synthesize a ResearchBrief preserving source attribution.
        4. Emit a RunManifest for the research run.
    """

    def __init__(
        self,
        bundle: RawSourceBundle,
        documents: Optional[NormalizedDocumentSet] = None,
        chunks: Optional[ChunkSet] = None,
        graph: Optional[KnowledgeGraphPackage] = None,
    ):
        self.bundle = bundle
        self.documents = documents
        self.chunks = chunks
        self.graph = graph

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
        topic = self.bundle.topic
        seed_entities = self.bundle.seed_entities or []

        # Default research question from topic
        if not research_question:
            research_question = f"What are the key aspects of: {topic}?"

        # Build source index and citation map from the bundle
        source_index = _build_source_index(self.bundle)
        citation_map = _build_citation_map(self.bundle)

        # Build entities
        if self.graph and self.graph.nodes:
            entities = _build_entities_from_graph(self.graph)
        else:
            entities = _build_entities_from_seeds(seed_entities, self.bundle)

        # Build key findings
        findings: List[KeyFinding] = []
        if self.documents and self.documents.documents:
            findings.extend(_build_findings_from_documents(self.documents))
        if not findings:
            findings = _build_placeholder_findings(topic, seed_entities)

        # Build executive summary
        entity_names = ", ".join(seed_entities[:5]) if seed_entities else "the topic"
        source_count = len(self.bundle.sources)
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
        recommended_angles = [
            f"Deep dive into {seed_entities[0]}" if seed_entities else "Broad topic overview",
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

        return RunManifest(
            artifact_id=_make_id("manifest"),
            created_at=_now_iso(),
            producer="content-research-pipeline",
            source_run_id=brief.source_run_id,
            pipeline_stage="generate-brief",
            status="completed",
            inputs={
                "raw_source_bundle": self.bundle.artifact_id,
                "documents": self.documents.artifact_id if self.documents else None,
                "chunks": self.chunks.artifact_id if self.chunks else None,
                "graph": self.graph.artifact_id if self.graph else None,
            },
            outputs=outputs,
            metrics={
                "source_count": len(self.bundle.sources),
                "finding_count": len(brief.key_findings),
                "entity_count": len(brief.entities),
            },
            errors=[],
        )


# ── Convenience function ─────────────────────────────────────────────────────

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
    run_manifest = generator.generate_run_manifest(brief)

    # Determine output paths
    out = Path(output_dir) if output_dir else Path(".")
    out.mkdir(parents=True, exist_ok=True)

    topic_slug = bundle.source_bundle_name or bundle.topic.replace(" ", "_").lower()
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
