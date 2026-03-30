"""
Phase 1.5 tests: upstream artifact consumption, fallback behavior,
and contract-valid output from KnowledgeGraphPackage and NormalizedDocumentSet.
"""

import json
import pytest
from pathlib import Path

from src.content_research_pipeline.data.artifacts import (
    GraphEdge,
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
    generate_brief_from_artifacts,
    load_knowledge_graph,
    load_normalized_document_set,
)
from src.content_research_pipeline.utils.contract_validator import (
    validate_research_brief,
    validate_run_manifest,
)


DEMO_DIR = (
    Path(__file__).parent.parent
    / "demo_data"
    / "jwst_star_formation_early_universe_demo"
)

CONTRACT_PATH = str(
    Path(__file__).parent.parent / "contracts" / "shared_artifacts.json"
)

DEMO_MANIFEST = DEMO_DIR / "manifest.json"
DEMO_KG = DEMO_DIR / "KnowledgeGraphPackage.sample.json"
DEMO_NDS = DEMO_DIR / "NormalizedDocumentSet.sample.json"


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _make_graph(num_nodes=3, num_edges=2):
    """Helper to create a test KnowledgeGraphPackage."""
    nodes = []
    for i in range(num_nodes):
        nodes.append(
            GraphNode(
                node_id=f"n-{i}",
                label=f"Node{i}",
                node_type="concept",
                description=f"Description of node {i}",
                source_refs=[SourceRef(source_id=f"src-{i % 2}")],
            )
        )
    edges = []
    for i in range(num_edges):
        edges.append(
            GraphEdge(
                edge_id=f"e-{i}",
                source_node_id=f"n-{i}",
                target_node_id=f"n-{i + 1}",
                relation_type="relates_to",
                weight=0.8,
                source_refs=[SourceRef(source_id=f"src-{i % 2}")],
            )
        )
    return KnowledgeGraphPackage(
        artifact_id="graph-test",
        created_at="2026-01-01T00:00:00Z",
        producer="test-ingestion",
        source_run_id="run-test",
        topic="Test Topic",
        graph_name="test-graph",
        nodes=nodes,
        edges=edges,
        provenance={"source": "test"},
    )


def _make_docs(num_docs=2):
    """Helper to create a test NormalizedDocumentSet."""
    documents = []
    for i in range(num_docs):
        documents.append(
            NormalizedDocument(
                document_id=f"doc-{i}",
                source_id=f"src-{i}",
                title=f"Document {i}",
                document_type="article",
                language="en",
                text=f"This is the full text content of document {i} about the test topic.",
            )
        )
    return NormalizedDocumentSet(
        artifact_id="docs-test",
        created_at="2026-01-01T00:00:00Z",
        producer="test-ingestion",
        source_run_id="run-test",
        topic="Test Topic",
        documents=documents,
    )


# ── KG-driven brief generation ──────────────────────────────────────────────

class TestKGDrivenBrief:
    """Test generating a ResearchBrief from a KnowledgeGraphPackage."""

    def test_kg_only_brief(self):
        """Brief can be generated from a KG alone, no bundle required."""
        graph = _make_graph()
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()

        assert isinstance(brief, ResearchBrief)
        assert brief.artifact_type == "ResearchBrief"
        assert brief.topic == "Test Topic"

    def test_kg_entities_from_nodes(self):
        """Entities should come from graph nodes."""
        graph = _make_graph(num_nodes=4)
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()

        assert len(brief.entities) == 4
        labels = {e["label"] for e in brief.entities}
        assert labels == {"Node0", "Node1", "Node2", "Node3"}

    def test_kg_findings_from_edges(self):
        """Key findings should include claims derived from graph edges."""
        graph = _make_graph(num_nodes=3, num_edges=2)
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()

        # Edges produce findings (2 edges) + nodes produce findings (3 nodes)
        assert len(brief.key_findings) >= 2
        edge_claims = [f.claim for f in brief.key_findings if "relates_to" in f.claim]
        assert len(edge_claims) == 2

    def test_kg_source_attribution(self):
        """Source index and citation map should be derived from graph source_refs."""
        graph = _make_graph()
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()

        source_ids = {s.source_id for s in brief.source_index}
        assert len(source_ids) > 0
        assert source_ids == set(brief.citation_map.keys())

    def test_kg_brief_contract_valid(self):
        """Brief generated from KG must pass contract validation."""
        graph = _make_graph()
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()
        data = brief.model_dump()

        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_kg_run_manifest_valid(self):
        """RunManifest from KG-only run must pass contract validation."""
        graph = _make_graph()
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        data = manifest.model_dump()

        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_kg_run_manifest_records_graph_input(self):
        """RunManifest should record graph artifact_id in inputs."""
        graph = _make_graph()
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        assert manifest.inputs["graph"] == "graph-test"
        assert manifest.inputs["raw_source_bundle"] is None

    def test_kg_with_bundle_merges_sources(self):
        """When both KG and bundle are provided, source info should merge."""
        bundle = _make_bundle(num_sources=2)
        graph = _make_graph(num_nodes=2)
        gen = BriefGenerator(bundle=bundle, graph=graph)
        brief = gen.generate()

        # Bundle provides richer source metadata, graph may add extra source_ids
        assert len(brief.source_index) >= 2
        assert len(brief.citation_map) >= 2

    def test_load_demo_kg_file(self):
        """Load the demo KnowledgeGraphPackage fixture."""
        graph = load_knowledge_graph(str(DEMO_KG))
        assert graph.artifact_type == "KnowledgeGraphPackage"
        assert len(graph.nodes) == 5
        assert len(graph.edges) == 4

    def test_demo_kg_generates_valid_brief(self):
        """End-to-end: demo KG produces a valid ResearchBrief."""
        graph = load_knowledge_graph(str(DEMO_KG))
        gen = BriefGenerator(graph=graph)
        brief = gen.generate()

        data = brief.model_dump()
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"
        assert len(brief.entities) == 5
        assert len(brief.key_findings) > 0


# ── NDS-driven brief generation ─────────────────────────────────────────────

class TestNDSDrivenBrief:
    """Test generating a ResearchBrief from a NormalizedDocumentSet."""

    def test_nds_only_brief(self):
        """Brief can be generated from NDS alone, no bundle required."""
        docs = _make_docs()
        gen = BriefGenerator(documents=docs)
        brief = gen.generate()

        assert isinstance(brief, ResearchBrief)
        assert brief.artifact_type == "ResearchBrief"
        assert brief.topic == "Test Topic"

    def test_nds_entities_from_documents(self):
        """Entities should be derived from document titles."""
        docs = _make_docs(num_docs=3)
        gen = BriefGenerator(documents=docs)
        brief = gen.generate()

        assert len(brief.entities) == 3
        labels = {e["label"] for e in brief.entities}
        assert "Document 0" in labels

    def test_nds_findings_from_text(self):
        """Key findings should be extracted from document text."""
        docs = _make_docs()
        gen = BriefGenerator(documents=docs)
        brief = gen.generate()

        assert len(brief.key_findings) >= 1
        assert any("Document" in f.claim for f in brief.key_findings)

    def test_nds_source_attribution(self):
        """Source index and citation map should be built from documents."""
        docs = _make_docs(num_docs=3)
        gen = BriefGenerator(documents=docs)
        brief = gen.generate()

        source_ids = {s.source_id for s in brief.source_index}
        assert len(source_ids) == 3
        assert source_ids == set(brief.citation_map.keys())

    def test_nds_brief_contract_valid(self):
        """Brief generated from NDS must pass contract validation."""
        docs = _make_docs()
        gen = BriefGenerator(documents=docs)
        brief = gen.generate()
        data = brief.model_dump()

        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_load_demo_nds_file(self):
        """Load the demo NormalizedDocumentSet fixture."""
        docs = load_normalized_document_set(str(DEMO_NDS))
        assert docs.artifact_type == "NormalizedDocumentSet"
        assert len(docs.documents) == 2

    def test_demo_nds_generates_valid_brief(self):
        """End-to-end: demo NDS produces a valid ResearchBrief."""
        docs = load_normalized_document_set(str(DEMO_NDS))
        gen = BriefGenerator(documents=docs)
        brief = gen.generate()

        data = brief.model_dump()
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"
        assert len(brief.key_findings) == 2


# ── Fallback behavior ───────────────────────────────────────────────────────

class TestFallbackBehavior:
    """Test the input priority / fallback chain."""

    def test_no_input_raises_error(self):
        """BriefGenerator must reject no inputs."""
        with pytest.raises(ValueError, match="At least one"):
            BriefGenerator()

    def test_kg_preferred_over_nds_for_entities(self):
        """When both KG and NDS are provided, entities come from KG."""
        docs = _make_docs(num_docs=2)
        graph = _make_graph(num_nodes=3)
        gen = BriefGenerator(documents=docs, graph=graph)
        brief = gen.generate()

        # Entities should be from graph, not documents
        assert len(brief.entities) == 3
        assert brief.entities[0]["entity_type"] == "concept"

    def test_kg_preferred_over_nds_for_findings(self):
        """When both KG and NDS are provided, findings come from KG."""
        docs = _make_docs(num_docs=2)
        graph = _make_graph(num_nodes=2, num_edges=1)
        gen = BriefGenerator(documents=docs, graph=graph)
        brief = gen.generate()

        # Findings should include graph-derived claims
        assert any("relates_to" in f.claim for f in brief.key_findings)

    def test_nds_preferred_over_bundle_for_entities(self):
        """When NDS and bundle are provided (no KG), entities come from NDS."""
        bundle = _make_bundle(seed_entities=["alpha", "beta"])
        docs = _make_docs(num_docs=2)
        gen = BriefGenerator(bundle=bundle, documents=docs)
        brief = gen.generate()

        # Entities should be document-topic, not seed
        assert len(brief.entities) == 2
        assert brief.entities[0]["entity_type"] == "document-topic"

    def test_nds_preferred_over_bundle_for_findings(self):
        """When NDS and bundle are provided, findings come from documents."""
        bundle = _make_bundle(seed_entities=["alpha"])
        docs = _make_docs(num_docs=1)
        gen = BriefGenerator(bundle=bundle, documents=docs)
        brief = gen.generate()

        assert any("Document" in f.claim for f in brief.key_findings)

    def test_bundle_fallback_for_entities(self):
        """When only bundle is provided, entities come from seed_entities."""
        bundle = _make_bundle(seed_entities=["alpha", "beta"])
        gen = BriefGenerator(bundle=bundle)
        brief = gen.generate()

        assert len(brief.entities) == 2
        labels = {e["label"] for e in brief.entities}
        assert labels == {"alpha", "beta"}

    def test_topic_priority_graph(self):
        """Topic should come from graph when available."""
        bundle = _make_bundle()
        graph = KnowledgeGraphPackage(
            artifact_id="graph-topic-test",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-test",
            topic="Graph Topic Override",
            graph_name="test-graph",
            nodes=[],
            edges=[],
            provenance={},
        )
        gen = BriefGenerator(bundle=bundle, graph=graph)
        brief = gen.generate()
        assert brief.topic == "Graph Topic Override"

    def test_topic_priority_nds(self):
        """Topic should come from NDS when no graph is available."""
        bundle = _make_bundle()
        docs = _make_docs()
        gen = BriefGenerator(bundle=bundle, documents=docs)
        # NDS and bundle both have "Test Topic"; NDS should not override
        # since there's no graph, NDS topic takes priority
        brief = gen.generate()
        assert brief.topic == "Test Topic"

    def test_source_index_merges_all_sources(self):
        """Source index should merge sources from all available artifacts."""
        bundle = _make_bundle(num_sources=2)
        # Graph references a source_id not in the bundle
        graph = KnowledgeGraphPackage(
            artifact_id="graph-merge-test",
            created_at="2026-01-01T00:00:00Z",
            producer="test",
            source_run_id="run-test",
            topic="Test Topic",
            graph_name="test-graph",
            nodes=[
                GraphNode(
                    node_id="n-extra",
                    label="Extra Node",
                    node_type="concept",
                    description="Node with a new source",
                    source_refs=[SourceRef(source_id="src-new-from-graph")],
                )
            ],
            provenance={},
        )
        gen = BriefGenerator(bundle=bundle, graph=graph)
        brief = gen.generate()

        source_ids = {s.source_id for s in brief.source_index}
        # Should have bundle sources + graph-only source
        assert "src-0" in source_ids
        assert "src-1" in source_ids
        assert "src-new-from-graph" in source_ids


# ── Contract output validation ───────────────────────────────────────────────

class TestContractOutput:
    """Test that all generation paths produce contract-valid output."""

    def _assert_brief_valid(self, brief: ResearchBrief):
        data = brief.model_dump()
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def _assert_manifest_valid(self, manifest: RunManifest):
        data = manifest.model_dump()
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_bundle_only_output(self):
        gen = BriefGenerator(bundle=_make_bundle())
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        self._assert_brief_valid(brief)
        self._assert_manifest_valid(manifest)

    def test_nds_only_output(self):
        gen = BriefGenerator(documents=_make_docs())
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        self._assert_brief_valid(brief)
        self._assert_manifest_valid(manifest)

    def test_kg_only_output(self):
        gen = BriefGenerator(graph=_make_graph())
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        self._assert_brief_valid(brief)
        self._assert_manifest_valid(manifest)

    def test_all_inputs_output(self):
        gen = BriefGenerator(
            bundle=_make_bundle(),
            documents=_make_docs(),
            graph=_make_graph(),
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        self._assert_brief_valid(brief)
        self._assert_manifest_valid(manifest)

    def test_brief_has_all_required_list_fields(self):
        gen = BriefGenerator(graph=_make_graph())
        brief = gen.generate()
        data = brief.model_dump()

        # All list fields must be lists, not None
        for field in ["key_findings", "entities", "timeline",
                      "source_index", "open_questions", "recommended_angles"]:
            assert isinstance(data[field], list), f"{field} should be a list"

        assert isinstance(data["citation_map"], dict)

    def test_brief_serialization_round_trip(self):
        gen = BriefGenerator(graph=_make_graph())
        brief = gen.generate()
        json_str = brief.model_dump_json(indent=2)
        data = json.loads(json_str)
        brief2 = ResearchBrief(**data)
        assert brief2.artifact_id == brief.artifact_id
        assert brief2.topic == brief.topic


# ── End-to-end convenience function ─────────────────────────────────────────

class TestGenerateBriefFromArtifacts:
    """Test the generate_brief_from_artifacts convenience function."""

    def test_from_manifest_only(self, tmp_path):
        result = generate_brief_from_artifacts(
            manifest_path=str(DEMO_MANIFEST),
            output_dir=str(tmp_path),
        )
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

    def test_from_graph_only(self, tmp_path):
        result = generate_brief_from_artifacts(
            graph_path=str(DEMO_KG),
            output_dir=str(tmp_path),
        )
        assert Path(result["brief_path"]).exists()
        brief = result["brief"]
        assert isinstance(brief, ResearchBrief)
        assert len(brief.entities) == 5

    def test_from_documents_only(self, tmp_path):
        result = generate_brief_from_artifacts(
            documents_path=str(DEMO_NDS),
            output_dir=str(tmp_path),
        )
        assert Path(result["brief_path"]).exists()
        brief = result["brief"]
        assert isinstance(brief, ResearchBrief)
        assert len(brief.key_findings) == 2

    def test_from_all_artifacts(self, tmp_path):
        result = generate_brief_from_artifacts(
            manifest_path=str(DEMO_MANIFEST),
            documents_path=str(DEMO_NDS),
            graph_path=str(DEMO_KG),
            output_dir=str(tmp_path),
        )
        brief = result["brief"]
        assert isinstance(brief, ResearchBrief)
        # Graph should drive entities
        assert len(brief.entities) == 5
        # Source index should merge all sources
        assert len(brief.source_index) >= 5

    def test_no_inputs_raises_error(self, tmp_path):
        with pytest.raises(ValueError, match="At least one"):
            generate_brief_from_artifacts(output_dir=str(tmp_path))

    def test_output_is_contract_valid(self, tmp_path):
        result = generate_brief_from_artifacts(
            graph_path=str(DEMO_KG),
            output_dir=str(tmp_path),
        )
        with open(result["brief_path"]) as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_output_filenames_follow_convention(self, tmp_path):
        result = generate_brief_from_artifacts(
            graph_path=str(DEMO_KG),
            output_dir=str(tmp_path),
        )
        brief_name = Path(result["brief_path"]).name
        assert "__ResearchBrief__" in brief_name
        assert brief_name.endswith(".json")


# ── Demo fixture contract validation ─────────────────────────────────────────

class TestDemoFixtureContract:
    """Validate the new demo fixture files against the shared contract."""

    def test_demo_kg_has_required_fields(self):
        with open(DEMO_KG) as f:
            data = json.load(f)
        contract = json.loads(Path(CONTRACT_PATH).read_text())
        required = contract["artifacts"]["KnowledgeGraphPackage"]["required_fields"]
        missing = [f for f in required if f not in data]
        assert not missing, f"Demo KG missing required fields: {missing}"

    def test_demo_kg_nodes_have_required_fields(self):
        with open(DEMO_KG) as f:
            data = json.load(f)
        contract = json.loads(Path(CONTRACT_PATH).read_text())
        node_required = contract["artifacts"]["KnowledgeGraphPackage"]["node_required_fields"]
        for i, node in enumerate(data["nodes"]):
            missing = [f for f in node_required if f not in node]
            assert not missing, f"Node [{i}] missing: {missing}"

    def test_demo_kg_edges_have_required_fields(self):
        with open(DEMO_KG) as f:
            data = json.load(f)
        contract = json.loads(Path(CONTRACT_PATH).read_text())
        edge_required = contract["artifacts"]["KnowledgeGraphPackage"]["edge_required_fields"]
        for i, edge in enumerate(data["edges"]):
            missing = [f for f in edge_required if f not in edge]
            assert not missing, f"Edge [{i}] missing: {missing}"

    def test_demo_nds_has_required_fields(self):
        with open(DEMO_NDS) as f:
            data = json.load(f)
        contract = json.loads(Path(CONTRACT_PATH).read_text())
        required = contract["artifacts"]["NormalizedDocumentSet"]["required_fields"]
        missing = [f for f in required if f not in data]
        assert not missing, f"Demo NDS missing required fields: {missing}"

    def test_demo_nds_documents_have_required_fields(self):
        with open(DEMO_NDS) as f:
            data = json.load(f)
        contract = json.loads(Path(CONTRACT_PATH).read_text())
        doc_required = contract["artifacts"]["NormalizedDocumentSet"]["document_required_fields"]
        for i, doc in enumerate(data["documents"]):
            missing = [f for f in doc_required if f not in doc]
            assert not missing, f"Document [{i}] missing: {missing}"
