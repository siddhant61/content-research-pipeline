"""
Phase 2B integration tests: consume the canonical upstream handoff package from
material-ingestion-pipeline and produce a contract-valid ResearchBrief.

Phase 2B adds:
* ChunkSet support in ``load_upstream_fixtures()``
* ``generate_brief_from_fixtures()`` convenience entry-point
* Canonical output fixtures written to a stable documented location
* Full upstream handoff → ResearchBrief → RunManifest round-trip

Test categories
---------------
* ChunkSet loading — ChunkSet discovery and loading via fixture loader.
* generate_brief_from_fixtures — end-to-end from UpstreamFixtures object.
* Chunks provenance — ChunkSet provenance flows into RunManifest.
* Canonical output fixtures — demo ResearchBrief.sample.json and
  RunManifest.sample.json are contract-valid and reflect real upstream data.
* Handoff round-trip — full end-to-end: load fixtures → generate → write → validate.
* Empty fixtures guard — ValueError raised when no artifacts loaded.

Contract assumptions
--------------------
* Demo fixtures conform to contracts/shared_artifacts.json v1.0.0.
* ChunkSet.chunks[].source_id cross-references NDS and bundle source_ids.
* ChunkSet provenance is captured in RunManifest.inputs.upstream_provenance.

Upstream files expected
-----------------------
Located in ``demo_data/jwst_star_formation_early_universe_demo/``:
* ``manifest.json``                       — RawSourceBundle (owned by material-ingestion)
* ``NormalizedDocumentSet.sample.json``   — NDS (owned by material-ingestion)
* ``ChunkSet.sample.json``               — ChunkSet (owned by material-ingestion) [Phase 2B]
* ``KnowledgeGraphPackage.sample.json``  — KG (owned by material-ingestion)

Downstream files emitted
------------------------
Located in ``demo_data/jwst_star_formation_early_universe_demo/``:
* ``ResearchBrief.sample.json``   — canonical ResearchBrief (owned by this repo)
* ``RunManifest.sample.json``     — canonical RunManifest (owned by this repo)
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
    generate_brief_from_fixtures,
)
from src.content_research_pipeline.data.artifacts import (
    ChunkSet,
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


# ── ChunkSet loading ─────────────────────────────────────────────────────────

class TestChunkSetFixtureLoading:
    """Test that load_upstream_fixtures discovers the ChunkSet artifact."""

    def test_chunks_loaded_from_demo_dir(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.chunks is not None, "ChunkSet.sample.json should be discovered"

    def test_chunks_path_is_set(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.chunks_path is not None
        assert "ChunkSet" in fixtures.chunks_path

    def test_chunks_shape(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert len(fixtures.chunks.chunks) == 6
        assert fixtures.chunks.artifact_id == "jwst-demo-chunks-001"
        assert fixtures.chunks.producer == "material-ingestion-pipeline"

    def test_chunks_topic_matches_other_fixtures(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.chunks.topic == fixtures.graph.topic

    def test_chunks_source_ids_reference_bundle(self):
        """ChunkSet source_ids should be a subset of bundle source_ids."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        bundle_ids = {s.source_id for s in fixtures.bundle.sources}
        chunk_ids = {c.source_id for c in fixtures.chunks.chunks}
        assert chunk_ids.issubset(bundle_ids), (
            f"Chunk source_ids not in bundle: {chunk_ids - bundle_ids}"
        )

    def test_chunks_document_ids_reference_nds(self):
        """ChunkSet document_ids should reference NDS document_ids."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        nds_doc_ids = {d.document_id for d in fixtures.documents.documents}
        chunk_doc_ids = {c.document_id for c in fixtures.chunks.chunks}
        assert chunk_doc_ids.issubset(nds_doc_ids), (
            f"Chunk document_ids not in NDS: {chunk_doc_ids - nds_doc_ids}"
        )

    def test_summary_includes_chunks(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        summary = fixtures.summary
        assert "chunks_loaded" in summary
        assert summary["chunks_loaded"] is True
        assert summary["chunks_path"] is not None

    def test_no_chunks_warns(self, tmp_path):
        """Fixture dir without ChunkSet emits a warning about ChunkSet."""
        import shutil
        shutil.copy(DEMO_DIR / "KnowledgeGraphPackage.sample.json", tmp_path)
        fixtures = load_upstream_fixtures(str(tmp_path))
        assert fixtures.chunks is None
        assert any(
            "ChunkSet" in w and "chunk-level provenance" in w
            for w in fixtures.warnings
        ), f"Expected ChunkSet warning, got: {fixtures.warnings}"

    def test_all_four_artifacts_loaded_from_demo(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.graph is not None
        assert fixtures.documents is not None
        assert fixtures.chunks is not None
        assert fixtures.bundle is not None
        assert fixtures.has_any


# ── generate_brief_from_fixtures ─────────────────────────────────────────────

@pytest.mark.integration
class TestGenerateBriefFromFixtures:
    """Test the generate_brief_from_fixtures() Phase 2B entry-point."""

    def test_returns_valid_brief(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_brief")
        brief = result["brief"]
        assert isinstance(brief, ResearchBrief)

    def test_returns_valid_manifest(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_manifest")
        manifest = result["run_manifest"]
        assert isinstance(manifest, RunManifest)

    def test_brief_contract_valid(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_contract")
        is_valid, errors = validate_research_brief(
            result["brief"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"ResearchBrief contract errors: {errors}"

    def test_manifest_contract_valid(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_manifest2")
        is_valid, errors = validate_run_manifest(
            result["run_manifest"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"RunManifest contract errors: {errors}"

    def test_output_files_written(self, tmp_path):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

    def test_output_brief_on_disk_is_valid(self, tmp_path):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        with open(result["brief_path"]) as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"On-disk ResearchBrief errors: {errors}"

    def test_result_includes_fixtures_key(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_fixtures")
        assert "fixtures" in result
        assert result["fixtures"] is fixtures

    def test_entities_from_kg(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_entities")
        assert len(result["brief"].entities) == 5

    def test_source_index_enriched_by_bundle(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir="/tmp/test_p2b_sources")
        by_id = {s.source_id: s for s in result["brief"].source_index}
        entry = by_id["jwst-nasa-mission-overview"]
        assert entry.origin_org == "NASA"
        assert entry.url.startswith("https://science.nasa.gov/")

    def test_empty_fixtures_raises(self, tmp_path):
        fixtures = load_upstream_fixtures(str(tmp_path))
        with pytest.raises(ValueError, match="no loaded artifacts"):
            generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))

    def test_research_question_override(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        custom_q = "How does JWST revolutionize our view of the cosmos?"
        result = generate_brief_from_fixtures(
            fixtures,
            research_question=custom_q,
            output_dir="/tmp/test_p2b_question",
        )
        assert result["brief"].research_question == custom_q


# ── Chunks provenance ─────────────────────────────────────────────────────────

@pytest.mark.integration
class TestChunksProvenancePreservation:
    """Test that ChunkSet provenance flows through to RunManifest."""

    def test_chunks_artifact_id_in_manifest_inputs(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            chunks=fixtures.chunks,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        assert manifest.inputs["chunks"] == "jwst-demo-chunks-001"

    def test_chunks_provenance_in_upstream_provenance(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            chunks=fixtures.chunks,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        upstream = manifest.inputs.get("upstream_provenance", {})
        assert upstream.get("chunks_producer") == "material-ingestion-pipeline"
        assert upstream.get("chunks_source_run_id") == "ingest-run-001"

    def test_all_four_inputs_recorded(self):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(
            bundle=fixtures.bundle,
            documents=fixtures.documents,
            chunks=fixtures.chunks,
            graph=fixtures.graph,
        )
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        assert manifest.inputs["graph"] == "jwst-demo-kg-001"
        assert manifest.inputs["documents"] == "jwst-demo-nds-001"
        assert manifest.inputs["chunks"] == "jwst-demo-chunks-001"
        assert manifest.inputs["raw_source_bundle"] == "jwst-star-formation-demo-source-bundle"

    def test_chunks_none_not_in_provenance(self):
        """Without chunks, chunks provenance keys should be absent."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        gen = BriefGenerator(graph=fixtures.graph)
        brief = gen.generate()
        manifest = gen.generate_run_manifest(brief)
        upstream = manifest.inputs.get("upstream_provenance", {})
        assert "chunks_producer" not in upstream


# ── Canonical output fixtures ─────────────────────────────────────────────────

class TestCanonicalOutputFixtures:
    """Verify the canonical demo ResearchBrief.sample.json and RunManifest.sample.json."""

    BRIEF_PATH = DEMO_DIR / "ResearchBrief.sample.json"
    MANIFEST_PATH = DEMO_DIR / "RunManifest.sample.json"

    def test_research_brief_sample_exists(self):
        assert self.BRIEF_PATH.exists(), "ResearchBrief.sample.json must exist"

    def test_run_manifest_sample_exists(self):
        assert self.MANIFEST_PATH.exists(), "RunManifest.sample.json must exist"

    def test_research_brief_sample_contract_valid(self):
        with open(self.BRIEF_PATH) as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Canonical ResearchBrief.sample.json invalid: {errors}"

    def test_run_manifest_sample_contract_valid(self):
        with open(self.MANIFEST_PATH) as f:
            data = json.load(f)
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Canonical RunManifest.sample.json invalid: {errors}"

    def test_research_brief_has_real_content(self):
        with open(self.BRIEF_PATH) as f:
            data = json.load(f)
        assert data["producer"] == "content-research-pipeline"
        assert len(data["key_findings"]) > 0
        assert len(data["entities"]) > 0
        assert len(data["source_index"]) > 0
        assert len(data["citation_map"]) > 0
        assert data["executive_summary"] != ""

    def test_run_manifest_has_real_content(self):
        with open(self.MANIFEST_PATH) as f:
            data = json.load(f)
        assert data["producer"] == "content-research-pipeline"
        assert data["status"] == "completed"
        assert data["inputs"].get("graph") == "jwst-demo-kg-001"
        assert data["inputs"].get("chunks") == "jwst-demo-chunks-001"
        assert data["metrics"]["finding_count"] > 0

    def test_brief_entities_from_kg(self):
        with open(self.BRIEF_PATH) as f:
            data = json.load(f)
        assert len(data["entities"]) == 5
        labels = {e["label"] for e in data["entities"]}
        assert "James Webb Space Telescope" in labels

    def test_brief_source_index_enriched(self):
        with open(self.BRIEF_PATH) as f:
            data = json.load(f)
        by_id = {s["source_id"]: s for s in data["source_index"]}
        assert by_id["jwst-nasa-mission-overview"]["origin_org"] == "NASA"

    def test_brief_artifact_type_correct(self):
        with open(self.BRIEF_PATH) as f:
            data = json.load(f)
        assert data["artifact_type"] == "ResearchBrief"

    def test_manifest_artifact_type_correct(self):
        with open(self.MANIFEST_PATH) as f:
            data = json.load(f)
        assert data["artifact_type"] == "RunManifest"

    def test_brief_upstream_provenance_recorded_in_manifest(self):
        with open(self.MANIFEST_PATH) as f:
            data = json.load(f)
        upstream = data["inputs"].get("upstream_provenance", {})
        assert upstream.get("graph_producer") == "material-ingestion-pipeline"
        assert upstream.get("chunks_producer") == "material-ingestion-pipeline"


# ── Full handoff round-trip ───────────────────────────────────────────────────

@pytest.mark.integration
class TestHandoffRoundTrip:
    """Full end-to-end: load all upstream fixtures → generate → write → validate."""

    def test_full_round_trip_with_all_artifacts(self, tmp_path):
        # 1. Load all upstream artifacts
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        assert fixtures.graph is not None
        assert fixtures.documents is not None
        assert fixtures.chunks is not None
        assert fixtures.bundle is not None

        # 2. Generate
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        manifest = result["run_manifest"]

        # 3. Validate brief on disk
        with open(result["brief_path"]) as f:
            brief_data = json.load(f)
        is_valid, errors = validate_research_brief(brief_data, CONTRACT_PATH)
        assert is_valid, f"Brief errors: {errors}"

        # 4. Validate manifest on disk
        with open(result["manifest_path"]) as f:
            manifest_data = json.load(f)
        is_valid2, errors2 = validate_run_manifest(manifest_data, CONTRACT_PATH)
        assert is_valid2, f"Manifest errors: {errors2}"

        # 5. Check provenance chain
        upstream = manifest.inputs.get("upstream_provenance", {})
        assert upstream["graph_producer"] == "material-ingestion-pipeline"
        assert upstream["chunks_producer"] == "material-ingestion-pipeline"
        assert upstream["documents_producer"] == "material-ingestion-pipeline"

    def test_round_trip_source_attribution_complete(self, tmp_path):
        """All 6 bundle sources should appear in source_index and citation_map."""
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        assert len(brief.source_index) >= 6
        assert len(brief.citation_map) >= 6

    def test_round_trip_kg_findings_have_evidence(self, tmp_path):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        high_confidence = [f for f in brief.key_findings if f.confidence >= 0.9]
        for finding in high_confidence:
            assert len(finding.evidence_refs) > 0, (
                f"High-confidence finding should have evidence_refs: {finding.claim}"
            )

    def test_round_trip_output_topic_matches_input(self, tmp_path):
        fixtures = load_upstream_fixtures(str(DEMO_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        assert result["brief"].topic == fixtures.graph.topic
