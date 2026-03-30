"""
Phase 2A integration tests: consume canonical upstream JWST fixture artifacts
from material-ingestion-pipeline and produce contract-valid ResearchBrief.

These tests use the canonical demo fixtures in
``demo_data/jwst_star_formation_early_universe_demo/`` (which simulate
real material-ingestion-pipeline output) rather than locally synthesised
test helpers.  This minimises fixture drift between repos.

Test categories
---------------
* Fixture loading — UpstreamFixtures discovery and loading.
* KG-driven integration — end-to-end from KnowledgeGraphPackage fixture.
* NDS fallback integration — end-to-end from NormalizedDocumentSet fixture.
* Combined artifact integration — all upstream artifacts together.
* Provenance preservation — upstream provenance flows into RunManifest.
* Citation enrichment — bundle metadata enriches KG-derived citations.
* CLI integration — --fixture-dir option.

Contract assumptions
--------------------
* Demo fixtures conform to contracts/shared_artifacts.json v1.0.0.
* KnowledgeGraphPackage.provenance carries upstream pipeline metadata.
* NormalizedDocumentSet.documents[].source_id cross-references
  RawSourceBundle.sources[].source_id.

Field degradations (documented)
-------------------------------
* KG-only path: source_index[].origin_org = "unknown", url = "".
* KG-only path: citation_map[].origin_org = "unknown", url = "", license = "unknown".
* These degrade gracefully when RawSourceBundle is also provided.
"""

import json
import pytest
from pathlib import Path

from src.content_research_pipeline.core.fixture_loader import (
    UpstreamFixtures,
    load_upstream_fixtures,
)
from src.content_research_pipeline.core.brief_generator import (
    BriefGenerator,
    generate_brief_from_artifacts,
)
from src.content_research_pipeline.data.artifacts import (
    ResearchBrief,
    RunManifest,
)
from src.content_research_pipeline.utils.contract_validator import (
    validate_research_brief,
    validate_run_manifest,
)


# ── Paths ────────────────────────────────────────────────────────────────────

DEMO_DIR = (
    Path(__file__).parent.parent
    / "demo_data"
    / "jwst_star_formation_early_universe_demo"
)

CONTRACT_PATH = str(
    Path(__file__).parent.parent / "contracts" / "shared_artifacts.json"
)


# ── Fixture loading ─────────────────────────────────────────────────────────

class TestFixtureLoading:
    """Test that load_upstream_fixtures discovers canonical demo artifacts."""

    def test_loads_all_three_artifacts(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.graph is not None, "KG should be discovered"
        assert fixtures.documents is not None, "NDS should be discovered"
        assert fixtures.bundle is not None, "Bundle should be discovered"
        assert fixtures.has_any

    def test_fixture_paths_are_set(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.graph_path is not None
        assert "KnowledgeGraphPackage" in fixtures.graph_path
        assert fixtures.documents_path is not None
        assert "NormalizedDocumentSet" in fixtures.documents_path
        assert fixtures.bundle_path is not None
        assert "manifest.json" in fixtures.bundle_path

    def test_fixture_dir_recorded(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.fixture_dir == str(DEMO_DIR)

    def test_summary_dict(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        summary = fixtures.summary
        assert summary["graph_loaded"] is True
        assert summary["documents_loaded"] is True
        assert summary["bundle_loaded"] is True

    def test_missing_dir_raises(self):
        with pytest.raises(FileNotFoundError):
            load_upstream_fixtures("/tmp/nonexistent_fixture_dir")

    def test_empty_dir_warnings(self, tmp_path):
        fixtures = load_upstream_fixtures(str(tmp_path))
        assert not fixtures.has_any
        assert any("No upstream fixtures" in w for w in fixtures.warnings)

    def test_kg_only_dir_warns_about_manifest(self, tmp_path):
        """When only a KG is present, warn about degraded source attribution."""
        import shutil
        shutil.copy(DEMO_DIR / "KnowledgeGraphPackage.sample.json", tmp_path)
        fixtures = load_upstream_fixtures(str(tmp_path))
        assert fixtures.graph is not None
        assert fixtures.bundle is None
        assert any("without manifest" in w for w in fixtures.warnings)

    def test_loaded_kg_matches_demo_shape(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert len(fixtures.graph.nodes) == 5
        assert len(fixtures.graph.edges) == 4
        assert fixtures.graph.producer == "material-ingestion-pipeline"

    def test_loaded_nds_matches_demo_shape(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert len(fixtures.documents.documents) == 2
        assert fixtures.documents.producer == "material-ingestion-pipeline"

    def test_loaded_bundle_matches_demo_shape(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert len(fixtures.bundle.sources) == 6
        assert fixtures.bundle.producer == "starter-pack"


# ── KG-driven integration ───────────────────────────────────────────────────

@pytest.mark.integration
class TestKGFixtureIntegration:
    """End-to-end: canonical JWST KG fixture → contract-valid ResearchBrief."""

    def test_kg_fixture_produces_valid_brief(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()

        assert isinstance(brief, ResearchBrief)
        data = brief.model_dump()
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_kg_fixture_entities_from_nodes(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()

        assert len(brief.entities) == 5
        labels = {e["label"] for e in brief.entities}
        assert "James Webb Space Telescope" in labels
        assert "star formation" in labels
        assert "early universe" in labels

    def test_kg_fixture_findings_from_edges(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()

        # 4 edges + 5 nodes = 9 findings
        assert len(brief.key_findings) == 9
        # Edge-derived findings use "label relation_type label" format
        edge_claims = [
            f for f in brief.key_findings
            if f.importance == "high" and f.confidence >= 0.9
        ]
        assert len(edge_claims) == 4

    def test_kg_fixture_source_refs_preserved(self):
        """Source_refs from KG nodes should appear in source_index."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()

        source_ids = {s.source_id for s in brief.source_index}
        assert "jwst-nasa-mission-overview" in source_ids
        assert "jwst-nasa-fact-sheet" in source_ids
        assert "jwst-nasa-video-star-formation" in source_ids

    def test_kg_only_field_degradation_documented(self):
        """Without bundle, KG-only source_index has degraded fields."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()

        for entry in brief.source_index:
            assert entry.origin_org == "unknown"
            assert entry.url == ""

    def test_kg_fixture_topic_preserved(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()

        assert "James Webb Space Telescope" in brief.topic

    def test_kg_fixture_run_manifest_valid(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        data = manifest.model_dump()
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_kg_fixture_end_to_end_write(self, tmp_path):
        """Full end-to-end: fixture → generate → write → validate on disk."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_artifacts(
            graph_path=fixtures.graph_path,
            output_dir=str(tmp_path),
        )
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

        with open(result["brief_path"]) as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract errors: {errors}"


# ── NDS fallback integration ────────────────────────────────────────────────

@pytest.mark.integration
class TestNDSFallbackIntegration:
    """End-to-end: canonical JWST NDS fixture → contract-valid ResearchBrief."""

    def test_nds_fixture_produces_valid_brief(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(documents=fixtures.documents)
        brief = gen.generate()

        data = brief.model_dump()
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_nds_fixture_findings_from_documents(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(documents=fixtures.documents)
        brief = gen.generate()

        assert len(brief.key_findings) == 2
        assert any("NASA Webb Mission Overview" in f.claim for f in brief.key_findings)
        assert any("NASA Webb Fact Sheet" in f.claim for f in brief.key_findings)

    def test_nds_fixture_source_ids_preserved(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(documents=fixtures.documents)
        brief = gen.generate()

        source_ids = {s.source_id for s in brief.source_index}
        assert "jwst-nasa-mission-overview" in source_ids
        assert "jwst-nasa-fact-sheet" in source_ids

    def test_nds_fixture_end_to_end_write(self, tmp_path):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_artifacts(
            documents_path=fixtures.documents_path,
            output_dir=str(tmp_path),
        )
        assert Path(result["brief_path"]).exists()

        with open(result["brief_path"]) as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract errors: {errors}"


# ── Combined artifact integration ────────────────────────────────────────────

@pytest.mark.integration
class TestCombinedFixtureIntegration:
    """End-to-end: all canonical JWST fixtures combined → enriched ResearchBrief."""

    def test_combined_produces_valid_brief(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()

        data = brief.model_dump()
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"

    def test_combined_entities_from_kg(self):
        """With all inputs, entities come from KG (highest priority)."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        assert len(brief.entities) == 5

    def test_combined_source_index_enriched(self):
        """Bundle metadata enriches source_index entries for KG source_ids."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()

        # All 6 bundle sources should appear, plus any extra from KG/NDS
        assert len(brief.source_index) >= 6

        # KG source_ids that overlap with bundle should have enriched metadata
        by_id = {s.source_id: s for s in brief.source_index}
        overview = by_id.get("jwst-nasa-mission-overview")
        assert overview is not None
        assert overview.origin_org == "NASA"
        assert "science.nasa.gov" in overview.url

    def test_combined_citation_map_enriched(self):
        """Bundle metadata enriches citation_map entries."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()

        cit = brief.citation_map.get("jwst-nasa-mission-overview")
        assert cit is not None
        assert cit["origin_org"] == "NASA"
        assert "science.nasa.gov" in cit["url"]

    def test_combined_end_to_end_write(self, tmp_path):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_artifacts(
            manifest_path=fixtures.bundle_path,
            documents_path=fixtures.documents_path,
            graph_path=fixtures.graph_path,
            output_dir=str(tmp_path),
        )
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

        brief = result["brief"]
        assert len(brief.entities) == 5
        assert len(brief.source_index) >= 6
        assert len(brief.citation_map) >= 6

    def test_combined_findings_have_evidence_refs(self):
        """Key findings should carry evidence_refs back to source_ids."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()

        for finding in brief.key_findings:
            if finding.confidence >= 0.7:
                assert len(finding.evidence_refs) > 0, (
                    f"Finding '{finding.claim}' should have evidence_refs"
                )


# ── Provenance preservation ──────────────────────────────────────────────────

@pytest.mark.integration
class TestProvenancePreservation:
    """Test that upstream provenance metadata is preserved in RunManifest."""

    def test_kg_provenance_in_run_manifest(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        upstream = manifest.inputs.get("upstream_provenance")
        assert upstream is not None
        assert upstream["graph_producer"] == "material-ingestion-pipeline"
        assert upstream["graph_source_run_id"] == "ingest-run-001"
        assert upstream["graph_provenance"]["pipeline"] == "material-ingestion-pipeline"
        assert upstream["graph_provenance"]["stage"] == "graph-construction"

    def test_combined_provenance_in_run_manifest(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        upstream = manifest.inputs.get("upstream_provenance")
        assert upstream is not None
        assert upstream["graph_producer"] == "material-ingestion-pipeline"
        assert upstream["documents_producer"] == "material-ingestion-pipeline"
        assert upstream["bundle_producer"] == "starter-pack"

    def test_nds_provenance_in_run_manifest(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(documents=fixtures.documents)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        upstream = manifest.inputs.get("upstream_provenance")
        assert upstream is not None
        assert upstream["documents_producer"] == "material-ingestion-pipeline"

    def test_run_manifest_records_artifact_ids(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        assert manifest.inputs["graph"] == "jwst-demo-kg-001"
        assert manifest.inputs["documents"] == "jwst-demo-nds-001"
        assert manifest.inputs["raw_source_bundle"] == "jwst-star-formation-demo-source-bundle"

    def test_run_manifest_contract_valid(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)

        data = manifest.model_dump()
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Contract validation errors: {errors}"


# ── Fixture contract conformance ─────────────────────────────────────────────

@pytest.mark.integration
class TestFixtureContractConformance:
    """Verify canonical demo fixture files conform to the shared contract."""

    def test_kg_fixture_producer_is_upstream(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.graph.producer == "material-ingestion-pipeline"

    def test_nds_fixture_producer_is_upstream(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.documents.producer == "material-ingestion-pipeline"

    def test_kg_source_refs_reference_bundle_source_ids(self):
        """KG source_refs should cross-reference bundle source_ids."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        bundle_source_ids = {s.source_id for s in fixtures.bundle.sources}
        kg_source_ids = set()
        for node in fixtures.graph.nodes:
            for ref in node.source_refs:
                kg_source_ids.add(ref.source_id)
        for edge in fixtures.graph.edges:
            for ref in edge.source_refs:
                kg_source_ids.add(ref.source_id)
        # All KG source_ids should be in the bundle
        assert kg_source_ids.issubset(bundle_source_ids), (
            f"KG source_ids not in bundle: {kg_source_ids - bundle_source_ids}"
        )

    def test_nds_source_ids_reference_bundle_source_ids(self):
        """NDS document source_ids should cross-reference bundle source_ids."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        bundle_source_ids = {s.source_id for s in fixtures.bundle.sources}
        nds_source_ids = {doc.source_id for doc in fixtures.documents.documents}
        assert nds_source_ids.issubset(bundle_source_ids), (
            f"NDS source_ids not in bundle: {nds_source_ids - bundle_source_ids}"
        )

    def test_all_fixtures_share_topic(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.graph.topic == fixtures.documents.topic
        assert fixtures.graph.topic == fixtures.bundle.topic
