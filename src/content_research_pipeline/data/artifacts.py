"""
Contract-aligned artifact models for the Content Research Pipeline.

These models match the shared artifact contract defined in contracts/shared_artifacts.json.
This repo owns: ResearchBrief, RunManifest (for research runs).
This repo consumes: RawSourceBundle, NormalizedDocumentSet, ChunkSet, KnowledgeGraphPackage.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ── Shared base fields (every artifact must include) ─────────────────────────

class ArtifactBase(BaseModel):
    """Base fields required by every artifact in the shared contract."""
    artifact_type: str
    schema_version: str = "1.0.0"
    artifact_id: str
    created_at: str
    producer: str
    source_run_id: str


# ── RawSourceBundle (consumed) ───────────────────────────────────────────────

class RawSourceItem(BaseModel):
    """A single source in a RawSourceBundle."""
    source_id: str
    title: str
    source_type: str
    origin_org: str
    url: str
    local_path: str
    mime_type: str
    language: str
    license: str
    usage_notes: str
    retrieved_at: Optional[str] = None
    checksum: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class RawSourceBundle(ArtifactBase):
    """Canonical list of raw source inputs for a topic (owned by ingestion)."""
    artifact_type: str = "RawSourceBundle"
    topic: str
    source_bundle_name: str
    sources: List[RawSourceItem] = Field(default_factory=list)
    # Optional fields present in demo scaffold
    status: Optional[str] = None
    notes: Optional[List[str]] = None
    seed_entities: Optional[List[str]] = None


# ── NormalizedDocumentSet (consumed) ─────────────────────────────────────────

class DocumentSection(BaseModel):
    """A section within a normalized document."""
    section_id: str
    heading: str
    text: str
    order_index: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    time_start: Optional[float] = None
    time_end: Optional[float] = None


class NormalizedDocument(BaseModel):
    """A single normalized document."""
    document_id: str
    source_id: str
    title: str
    document_type: str
    language: str
    text: str
    sections: List[DocumentSection] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedDocumentSet(ArtifactBase):
    """Set of normalized documents (owned by ingestion)."""
    artifact_type: str = "NormalizedDocumentSet"
    topic: str
    documents: List[NormalizedDocument] = Field(default_factory=list)


# ── ChunkSet (consumed) ─────────────────────────────────────────────────────

class Chunk(BaseModel):
    """A single chunk from the ChunkSet."""
    chunk_id: str
    document_id: str
    source_id: str
    text: str
    token_count: int
    char_count: int
    embedding_model: str
    embedding_vector_ref: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkSet(ArtifactBase):
    """Set of chunked documents (owned by ingestion)."""
    artifact_type: str = "ChunkSet"
    topic: str
    chunking_strategy: str
    chunks: List[Chunk] = Field(default_factory=list)


# ── KnowledgeGraphPackage (consumed) ────────────────────────────────────────

class SourceRef(BaseModel):
    """A reference back to a source document/chunk."""
    source_id: str
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    quote: Optional[str] = None
    confidence: Optional[float] = None


class GraphNode(BaseModel):
    """A node in the knowledge graph."""
    node_id: str
    label: str
    node_type: str
    description: str
    aliases: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    source_refs: List[SourceRef] = Field(default_factory=list)


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    weight: float = 1.0
    evidence: Optional[str] = None
    source_refs: List[SourceRef] = Field(default_factory=list)


class KnowledgeGraphPackage(ArtifactBase):
    """Knowledge graph package (owned by ingestion)."""
    artifact_type: str = "KnowledgeGraphPackage"
    topic: str
    graph_name: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    embeddings_index: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


# ── ResearchBrief (owned by this repo) ──────────────────────────────────────

class KeyFinding(BaseModel):
    """A single key finding in the research brief."""
    finding_id: str
    claim: str
    importance: str
    confidence: float = 0.0
    evidence_refs: List[str] = Field(default_factory=list)


class SourceIndexEntry(BaseModel):
    """An entry in the source index of the research brief."""
    source_id: str
    title: str
    origin_org: str
    url: str
    source_type: str
    credibility_notes: str = ""


class TimelineEntry(BaseModel):
    """A timeline event in the research brief."""
    date: str
    event: str
    source_ref: Optional[str] = None


class ResearchBrief(ArtifactBase):
    """
    The primary output artifact owned by content-research-pipeline.

    Consumed by media-generation-pipeline to create ScenePlan and MediaPackage.
    """
    artifact_type: str = "ResearchBrief"
    topic: str
    research_question: str
    executive_summary: str
    key_findings: List[KeyFinding] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    timeline: List[TimelineEntry] = Field(default_factory=list)
    source_index: List[SourceIndexEntry] = Field(default_factory=list)
    citation_map: Dict[str, Any] = Field(default_factory=dict)
    open_questions: List[str] = Field(default_factory=list)
    recommended_angles: List[str] = Field(default_factory=list)


# ── RunManifest (owned by all pipelines) ────────────────────────────────────

class RunManifest(ArtifactBase):
    """
    Tracking artifact emitted by each pipeline run.

    Records inputs, outputs, status, and metrics for a single pipeline execution.
    """
    artifact_type: str = "RunManifest"
    pipeline_name: str = "content-research-pipeline"
    pipeline_stage: str
    status: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
