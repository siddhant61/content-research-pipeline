"""
Tests for the brief generator module.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from src.content_research_pipeline.data.artifacts import (
    ChunkSet,
    GraphNode,
    KnowledgeGraphPackage,
    NormalizedDocument,
    NormalizedDocumentSet,
    RawSourceBundle,
    RawSourceItem,
    ResearchBrief,
    RunManifest,
    SourceRef,
)
from src.content_research_pipeline.core.brief_generator import (
    BriefGenerator,
    generate_brief_from_manifest,
    load_raw_source_bundle,
)


DEMO_MANIFEST = (
    Path(__file__).parent.parent
    / "demo_data"
    / "jwst_star_formation_early_universe_demo"
    / "manifest.json"
)


def _make_bundle(num_sources=2, seed_entities=None):
    """Helper to create a test RawSourceBundle."""
    sources = []
    for i in range(num_sources):
        sources.append(
            RawSourceItem(
                source_id=f"src-{i}",
                title=f"Source {i}",
                source_type="webpage",
                origin_org=f"Org{i}",
                url=f"https://example.com/{i}",
                local_path=f"sources/web/source_{i}.html",
                mime_type="text/html",
                language="en",
                license="MIT",
                usage_notes=f"Test source {i}",
            )
        )
    if seed_entities is None:
        seed_entities = ["entity_a", "entity_b"]
    return RawSourceBundle(
        artifact_id="bundle-test",
        created_at="2026-01-01T00:00:00Z",
        producer="test",
        source_run_id="run-test",
        topic="Test Topic",
        source_bundle_name="test_topic",
        sources=sources,
        seed_entities=seed_entities,
    )


class TestLoadRawSourceBundle:
    """Test loading a RawSourceBundle from disk."""

    def test_load_demo_manifest(self):
        bundle = load_raw_source_bundle(str(DEMO_MANIFEST))
        assert bundle.artifact_type == "RawSourceBundle"
        assert len(bundle.sources) == 6
        assert bundle.topic.startswith("James Webb")

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_raw_source_bundle("/nonexistent/manifest.json")


class TestBriefGenerator:
    """Test BriefGenerator class."""

    def test_generate_minimal(self):
        bundle = _make_bundle()
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()

        assert isinstance(brief, ResearchBrief)
        assert brief.artifact_type == "ResearchBrief"
        assert brief.schema_version == "1.0.0"
        assert brief.topic == "Test Topic"
        assert len(brief.source_index) == 2
        assert len(brief.citation_map) == 2
        assert len(brief.entities) == 2

    def test_generate_preserves_source_attribution(self):
        bundle = _make_bundle(num_sources=3)
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()

        # source_index should have all 3 sources
        assert len(brief.source_index) == 3
        source_ids = {s.source_id for s in brief.source_index}
        assert source_ids == {"src-0", "src-1", "src-2"}

        # citation_map should have all 3 sources
        assert set(brief.citation_map.keys()) == {"src-0", "src-1", "src-2"}

    def test_generate_custom_question(self):
        bundle = _make_bundle()
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate(research_question="What is the meaning of life?")
        assert brief.research_question == "What is the meaning of life?"

    def test_generate_default_question(self):
        bundle = _make_bundle()
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()
        assert "Test Topic" in brief.research_question

    def test_generate_with_knowledge_graph(self):
        bundle = _make_bundle()
        graph = KnowledgeGraphPackage(
            artifact_id="graph-test",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-test",
            topic="Test Topic",
            graph_name="test-graph",
            nodes=[
                GraphNode(
                    node_id="n1",
                    label="Alpha",
                    node_type="concept",
                    description="First node",
                    source_refs=[SourceRef(source_id="src-0")],
                ),
                GraphNode(
                    node_id="n2",
                    label="Beta",
                    node_type="concept",
                    description="Second node",
                    source_refs=[],
                ),
            ],
        )
        gen = BriefGenerator(bundle=bundle, graph=graph)
        brief = gen.generate()

        # Should use graph entities, not seed entities
        assert len(brief.entities) == 2
        labels = {e["label"] for e in brief.entities}
        assert labels == {"Alpha", "Beta"}

    def test_generate_with_documents(self):
        bundle = _make_bundle()
        docs = NormalizedDocumentSet(
            artifact_id="docs-test",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-test",
            topic="Test Topic",
            documents=[
                NormalizedDocument(
                    document_id="doc-1",
                    source_id="src-0",
                    title="Test Document",
                    document_type="article",
                    language="en",
                    text="This is a test document about a very important topic.",
                )
            ],
        )
        gen = BriefGenerator(bundle=bundle, documents=docs)
        brief = gen.generate()

        # Should have findings from documents
        assert len(brief.key_findings) >= 1
        assert any("Test Document" in f.claim for f in brief.key_findings)

    def test_generate_empty_seeds(self):
        bundle = _make_bundle(seed_entities=[])
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()
        # Should still work, just with empty entities
        assert isinstance(brief, ResearchBrief)
        assert len(brief.entities) == 0

    def test_run_manifest_generation(self):
        bundle = _make_bundle()
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief, output_path="output/brief.json")

        assert isinstance(manifest, RunManifest)
        assert manifest.artifact_type == "RunManifest"
        assert manifest.pipeline_name == "content-research-pipeline"
        assert manifest.pipeline_stage == "generate-brief"
        assert manifest.status == "completed"
        assert manifest.inputs["raw_source_bundle"] == "bundle-test"
        assert "output/brief.json" in manifest.outputs
        assert manifest.metrics["source_count"] == 2

    def test_run_manifest_without_output_path(self):
        bundle = _make_bundle()
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        assert manifest.outputs == []


class TestGenerateBriefFromManifest:
    """Test the convenience function end-to-end."""

    def test_end_to_end_demo_manifest(self, tmp_path):
        result = generate_brief_from_manifest(
            manifest_path=str(DEMO_MANIFEST),
            output_dir=str(tmp_path),
        )

        assert "brief" in result
        assert "run_manifest" in result
        assert "brief_path" in result
        assert "manifest_path" in result

        # Files should exist
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

        # Brief should be valid JSON
        with open(result["brief_path"]) as f:
            data = json.load(f)
        assert data["artifact_type"] == "ResearchBrief"
        assert data["schema_version"] == "1.0.0"
        assert len(data["source_index"]) == 6

    def test_end_to_end_with_custom_question(self, tmp_path):
        result = generate_brief_from_manifest(
            manifest_path=str(DEMO_MANIFEST),
            research_question="How does JWST observe star formation?",
            output_dir=str(tmp_path),
        )
        assert result["brief"].research_question == "How does JWST observe star formation?"

    def test_output_filenames_follow_convention(self, tmp_path):
        result = generate_brief_from_manifest(
            manifest_path=str(DEMO_MANIFEST),
            output_dir=str(tmp_path),
        )
        brief_name = Path(result["brief_path"]).name
        manifest_name = Path(result["manifest_path"]).name

        assert "__ResearchBrief__" in brief_name
        assert "__RunManifest__" in manifest_name
        assert brief_name.startswith("jwst_star_formation_early_universe_demo")
        assert brief_name.endswith(".json")
