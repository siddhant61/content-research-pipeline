"""
Tests for contract-aligned artifact models.
"""

import pytest
from src.content_research_pipeline.data.artifacts import (
    ArtifactBase,
    ChunkSet,
    GraphEdge,
    GraphNode,
    KeyFinding,
    KnowledgeGraphPackage,
    NormalizedDocument,
    NormalizedDocumentSet,
    RawSourceBundle,
    RawSourceItem,
    ResearchBrief,
    RunManifest,
    SourceIndexEntry,
    SourceRef,
    TimelineEntry,
)


class TestArtifactBase:
    """Test the artifact base model."""

    def test_base_fields(self):
        base = ArtifactBase(
            artifact_type="TestArtifact",
            schema_version="1.0.0",
            artifact_id="test-001",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-001",
        )
        assert base.artifact_type == "TestArtifact"
        assert base.schema_version == "1.0.0"
        assert base.artifact_id == "test-001"


class TestResearchBrief:
    """Test the ResearchBrief model."""

    def test_minimal_brief(self):
        brief = ResearchBrief(
            artifact_id="brief-001",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-001",
            topic="test topic",
            research_question="What is the test about?",
            executive_summary="Test summary",
        )
        assert brief.artifact_type == "ResearchBrief"
        assert brief.topic == "test topic"
        assert brief.key_findings == []
        assert brief.entities == []
        assert brief.timeline == []
        assert brief.source_index == []
        assert brief.citation_map == {}
        assert brief.open_questions == []
        assert brief.recommended_angles == []

    def test_full_brief(self):
        brief = ResearchBrief(
            artifact_id="brief-002",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-002",
            topic="JWST demo",
            research_question="How does JWST work?",
            executive_summary="JWST is a space telescope.",
            key_findings=[
                KeyFinding(
                    finding_id="f1",
                    claim="JWST uses infrared sensors",
                    importance="high",
                    confidence=0.9,
                    evidence_refs=["src-1"],
                )
            ],
            entities=[{"entity_id": "e1", "label": "JWST"}],
            timeline=[TimelineEntry(date="2021-12-25", event="Launch")],
            source_index=[
                SourceIndexEntry(
                    source_id="src-1",
                    title="NASA Overview",
                    origin_org="NASA",
                    url="https://nasa.gov/jwst",
                    source_type="webpage",
                )
            ],
            citation_map={"src-1": {"title": "NASA Overview"}},
            open_questions=["What next?"],
            recommended_angles=["Deep dive"],
        )
        assert len(brief.key_findings) == 1
        assert brief.key_findings[0].confidence == 0.9
        assert len(brief.source_index) == 1
        assert "src-1" in brief.citation_map

    def test_brief_serialization(self):
        brief = ResearchBrief(
            artifact_id="brief-ser",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-ser",
            topic="test",
            research_question="test?",
            executive_summary="summary",
        )
        data = brief.model_dump()
        assert data["artifact_type"] == "ResearchBrief"
        assert data["schema_version"] == "1.0.0"
        # Round-trip
        brief2 = ResearchBrief(**data)
        assert brief2.artifact_id == brief.artifact_id


class TestRunManifest:
    """Test the RunManifest model."""

    def test_minimal_manifest(self):
        manifest = RunManifest(
            artifact_id="manifest-001",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-001",
            pipeline_stage="test",
            status="completed",
        )
        assert manifest.artifact_type == "RunManifest"
        assert manifest.pipeline_name == "content-research-pipeline"
        assert manifest.inputs == {}
        assert manifest.outputs == []
        assert manifest.metrics == {}
        assert manifest.errors == []

    def test_manifest_with_data(self):
        manifest = RunManifest(
            artifact_id="manifest-002",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-002",
            pipeline_stage="generate-brief",
            status="completed",
            inputs={"raw_source_bundle": "bundle-001"},
            outputs=["brief.json"],
            metrics={"source_count": 5},
            errors=[],
        )
        assert manifest.inputs["raw_source_bundle"] == "bundle-001"
        assert len(manifest.outputs) == 1


class TestRawSourceBundle:
    """Test the RawSourceBundle model."""

    def test_parse_demo_manifest(self):
        import json
        from pathlib import Path

        manifest_path = Path(__file__).parent.parent / "demo_data" / "jwst_star_formation_early_universe_demo" / "manifest.json"
        with open(manifest_path) as f:
            data = json.load(f)

        bundle = RawSourceBundle(**data)
        assert bundle.artifact_type == "RawSourceBundle"
        assert len(bundle.sources) == 6
        assert bundle.seed_entities is not None
        assert len(bundle.seed_entities) == 10
        assert bundle.sources[0].source_id == "jwst-nasa-mission-overview"


class TestKnowledgeGraphPackage:
    """Test the KnowledgeGraphPackage model."""

    def test_graph_with_nodes_edges(self):
        graph = KnowledgeGraphPackage(
            artifact_id="graph-001",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-001",
            topic="test",
            graph_name="test-graph",
            nodes=[
                GraphNode(
                    node_id="n1",
                    label="JWST",
                    node_type="telescope",
                    description="A space telescope",
                    source_refs=[SourceRef(source_id="src-1")],
                )
            ],
            edges=[
                GraphEdge(
                    edge_id="e1",
                    source_node_id="n1",
                    target_node_id="n2",
                    relation_type="observes",
                )
            ],
        )
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1
        assert graph.nodes[0].source_refs[0].source_id == "src-1"
