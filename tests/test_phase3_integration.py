"""
Phase 3 integration tests: consume the upstream handoff package and emit the
canonical downstream handoff package for media-generation.

Phase 3 adds:
* ``load_from_handoff_manifest()`` in ``fixture_loader.py``
* ``generate_downstream_handoff_manifest()`` in ``brief_generator.py``
* ``--upstream-handoff-dir`` / ``--emit-handoff-manifest`` in ``brief_cli.py``
* Canonical integration fixtures in ``integration_fixtures/jwst/``

Test categories
---------------
* Upstream handoff loading — load_from_handoff_manifest reads declared artifacts.
* Downstream handoff generation — generate_downstream_handoff_manifest emits valid JSON.
* Round-trip — full upstream→downstream pipeline: load → generate → emit → validate.
* Canonical downstream fixtures — integration_fixtures/jwst/downstream/ are contract-valid.
* Handoff manifest contract — upstream and downstream handoff_manifest.json fields.
* Fallback — directories without handoff_manifest fall back to auto-discovery.

Contract assumptions
--------------------
* integration_fixtures/jwst/upstream/handoff_manifest.json lists 4 artifacts.
* integration_fixtures/jwst/downstream/ contains ResearchBrief.json, RunManifest.json,
  and handoff_manifest.json (all pre-generated and stable).
* All artifact files conform to contracts/shared_artifacts.json v1.0.0.

Upstream files consumed
-----------------------
Located in ``integration_fixtures/jwst/upstream/``:
* ``handoff_manifest.json``         — upstream handoff manifest (Phase 3)
* ``KnowledgeGraphPackage.json``    — KG (owned by material-ingestion)
* ``NormalizedDocumentSet.json``    — NDS (owned by material-ingestion)
* ``ChunkSet.json``                  — ChunkSet (owned by material-ingestion)
* ``RawSourceBundle.json``          — RawSourceBundle (owned by material-ingestion)

Downstream files emitted (canonical fixtures)
----------------------------------------------
Located in ``integration_fixtures/jwst/downstream/``:
* ``handoff_manifest.json``         — downstream handoff manifest (for media-generation)
* ``ResearchBrief.json``            — canonical ResearchBrief (owned by this repo)
* ``RunManifest.json``              — canonical RunManifest (owned by this repo)
"""

import json
import shutil
import pytest
from pathlib import Path

from src.content_research_pipeline.core.fixture_loader import (
    UpstreamFixtures,
    load_from_handoff_manifest,
    load_upstream_fixtures,
)
from src.content_research_pipeline.core.brief_generator import (
    BriefGenerator,
    generate_brief_from_fixtures,
    generate_downstream_handoff_manifest,
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

UPSTREAM_DIR = (
    Path(__file__).parent.parent / "integration_fixtures" / "jwst" / "upstream"
)
DOWNSTREAM_DIR = (
    Path(__file__).parent.parent / "integration_fixtures" / "jwst" / "downstream"
)
CONTRACT_PATH = str(
    Path(__file__).parent.parent / "contracts" / "shared_artifacts.json"
)


# ── Upstream handoff loading ──────────────────────────────────────────────────

class TestLoadFromHandoffManifest:
    """Test that load_from_handoff_manifest reads declared artifacts correctly."""

    def test_all_artifacts_loaded(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.graph is not None, "KnowledgeGraphPackage should be loaded"
        assert fixtures.documents is not None, "NormalizedDocumentSet should be loaded"
        assert fixtures.chunks is not None, "ChunkSet should be loaded"
        assert fixtures.bundle is not None, "RawSourceBundle should be loaded"

    def test_has_any_true(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.has_any

    def test_fixture_dir_set(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert str(UPSTREAM_DIR) in fixtures.fixture_dir

    def test_graph_paths_set(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.graph_path is not None
        assert "KnowledgeGraphPackage.json" in fixtures.graph_path

    def test_documents_path_set(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.documents_path is not None
        assert "NormalizedDocumentSet.json" in fixtures.documents_path

    def test_chunks_path_set(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.chunks_path is not None
        assert "ChunkSet.json" in fixtures.chunks_path

    def test_bundle_path_set(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.bundle_path is not None
        assert "RawSourceBundle.json" in fixtures.bundle_path

    def test_artifact_ids_match_handoff_manifest(self):
        with open(UPSTREAM_DIR / "handoff_manifest.json") as f:
            manifest = json.load(f)
        declared_ids = {e["artifact_id"] for e in manifest["artifacts"]}

        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        loaded_ids = {
            a.artifact_id
            for a in [fixtures.graph, fixtures.documents, fixtures.chunks, fixtures.bundle]
            if a is not None
        }
        assert loaded_ids == declared_ids, (
            f"Loaded artifact_ids {loaded_ids} differ from declared {declared_ids}"
        )

    def test_topics_consistent(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        topics = {
            a.topic
            for a in [fixtures.graph, fixtures.documents, fixtures.chunks]
            if a is not None
        }
        assert len(topics) == 1, f"Multiple distinct topics found: {topics}"

    def test_all_artifacts_from_material_ingestion(self):
        """All upstream artifacts should declare material-ingestion-pipeline as producer."""
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        for artifact in [fixtures.graph, fixtures.documents, fixtures.chunks]:
            assert artifact.producer == "material-ingestion-pipeline", (
                f"{type(artifact).__name__} producer is '{artifact.producer}'"
            )

    def test_missing_dir_raises(self):
        with pytest.raises(FileNotFoundError):
            load_from_handoff_manifest("/nonexistent/path/that/does/not/exist")

    def test_handoff_manifest_schema_fields(self):
        with open(UPSTREAM_DIR / "handoff_manifest.json") as f:
            manifest = json.load(f)
        assert manifest["schema_version"] == "1.0.0"
        assert manifest["handoff_type"] == "upstream"
        assert manifest["pipeline"] == "material-ingestion-pipeline"
        assert manifest["produced_for"] == "content-research-pipeline"
        assert "topic" in manifest
        assert "source_run_id" in manifest
        assert "artifacts" in manifest
        assert "regeneration_command" in manifest
        assert "validation_command" in manifest
        assert "known_limitations" in manifest

    def test_upstream_artifacts_list_non_empty(self):
        with open(UPSTREAM_DIR / "handoff_manifest.json") as f:
            manifest = json.load(f)
        assert len(manifest["artifacts"]) > 0

    def test_required_artifact_has_required_true(self):
        with open(UPSTREAM_DIR / "handoff_manifest.json") as f:
            manifest = json.load(f)
        required = [a for a in manifest["artifacts"] if a.get("required")]
        assert len(required) >= 1, "At least one artifact should be marked required"
        kg_entries = [a for a in required if a["artifact_type"] == "KnowledgeGraphPackage"]
        assert len(kg_entries) == 1, "KnowledgeGraphPackage should be required"


class TestHandoffManifestFallback:
    """load_from_handoff_manifest falls back to auto-discovery without handoff_manifest.json."""

    def test_fallback_to_auto_discovery(self, tmp_path):
        shutil.copy(
            UPSTREAM_DIR / "KnowledgeGraphPackage.json",
            tmp_path / "KnowledgeGraphPackage.json",
        )
        fixtures = load_from_handoff_manifest(str(tmp_path))
        assert fixtures.graph is not None
        assert fixtures.documents is None

    def test_fallback_matches_load_upstream_fixtures(self, tmp_path):
        shutil.copy(
            UPSTREAM_DIR / "KnowledgeGraphPackage.json",
            tmp_path / "KnowledgeGraphPackage.sample.json",
        )
        fixtures_handoff = load_from_handoff_manifest(str(tmp_path))
        fixtures_auto = load_upstream_fixtures(str(tmp_path))
        assert (fixtures_handoff.graph is not None) == (fixtures_auto.graph is not None)

    def test_missing_optional_artifact_warns_not_raises(self, tmp_path):
        """A missing non-required artifact should warn but not raise."""
        manifest = {
            "schema_version": "1.0.0",
            "handoff_type": "upstream",
            "artifacts": [
                {
                    "artifact_type": "KnowledgeGraphPackage",
                    "artifact_id": "kg-001",
                    "path": "KnowledgeGraphPackage.json",
                    "required": True,
                },
                {
                    "artifact_type": "NormalizedDocumentSet",
                    "artifact_id": "nds-001",
                    "path": "NDS_does_not_exist.json",
                    "required": False,
                },
            ],
        }
        (tmp_path / "handoff_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        shutil.copy(
            UPSTREAM_DIR / "KnowledgeGraphPackage.json",
            tmp_path / "KnowledgeGraphPackage.json",
        )
        fixtures = load_from_handoff_manifest(str(tmp_path))
        assert fixtures.graph is not None
        assert fixtures.documents is None
        assert any("NDS_does_not_exist.json" in w for w in fixtures.warnings)

    def test_missing_required_artifact_raises(self, tmp_path):
        """A missing required artifact should raise FileNotFoundError."""
        manifest = {
            "schema_version": "1.0.0",
            "handoff_type": "upstream",
            "artifacts": [
                {
                    "artifact_type": "KnowledgeGraphPackage",
                    "artifact_id": "kg-001",
                    "path": "KG_does_not_exist.json",
                    "required": True,
                }
            ],
        }
        (tmp_path / "handoff_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        with pytest.raises(FileNotFoundError, match="KG_does_not_exist.json"):
            load_from_handoff_manifest(str(tmp_path))


# ── Downstream handoff generation ────────────────────────────────────────────

@pytest.mark.integration
class TestGenerateDownstreamHandoffManifest:
    """Test generate_downstream_handoff_manifest() output structure."""

    def _make_result(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        return generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))

    def test_handoff_manifest_written(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
            upstream_source_run_id="ingest-run-001",
        )
        assert Path(hm_result["handoff_manifest_path"]).exists()

    def test_handoff_manifest_schema_version(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        assert hm_result["handoff_manifest"]["schema_version"] == "1.0.0"

    def test_handoff_type_is_downstream(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        assert hm_result["handoff_manifest"]["handoff_type"] == "downstream"

    def test_produced_for_media_generation(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        assert hm_result["handoff_manifest"]["produced_for"] == "media-generation-pipeline"

    def test_pipeline_is_content_research(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        assert hm_result["handoff_manifest"]["pipeline"] == "content-research-pipeline"

    def test_artifacts_list_has_research_brief(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        types = [a["artifact_type"] for a in hm_result["handoff_manifest"]["artifacts"]]
        assert "ResearchBrief" in types

    def test_artifacts_list_has_run_manifest(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        types = [a["artifact_type"] for a in hm_result["handoff_manifest"]["artifacts"]]
        assert "RunManifest" in types

    def test_research_brief_artifact_is_required(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        rb_entries = [
            a for a in hm_result["handoff_manifest"]["artifacts"]
            if a["artifact_type"] == "ResearchBrief"
        ]
        assert rb_entries[0]["required"] is True

    def test_regeneration_command_present(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        assert "regeneration_command" in hm_result["handoff_manifest"]
        assert len(hm_result["handoff_manifest"]["regeneration_command"]) > 0

    def test_validation_command_present(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        assert "validation_command" in hm_result["handoff_manifest"]
        assert "brief_cli" in hm_result["handoff_manifest"]["validation_command"]

    def test_known_limitations_list(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        limitations = hm_result["handoff_manifest"]["known_limitations"]
        assert isinstance(limitations, list)
        assert len(limitations) > 0

    def test_upstream_source_run_id_preserved(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
            upstream_source_run_id="ingest-run-001",
        )
        assert hm_result["handoff_manifest"]["upstream_source_run_id"] == "ingest-run-001"

    def test_artifact_ids_match_generated_artifacts(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        declared_ids = {a["artifact_id"] for a in hm_result["handoff_manifest"]["artifacts"]}
        assert result["brief"].artifact_id in declared_ids
        assert result["run_manifest"].artifact_id in declared_ids

    def test_artifact_paths_resolve_to_existing_files(self, tmp_path):
        result = self._make_result(tmp_path)
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
        )
        for artifact in hm_result["handoff_manifest"]["artifacts"]:
            artifact_path = tmp_path / artifact["path"]
            assert artifact_path.exists(), (
                f"Artifact path does not exist: {artifact_path}"
            )


# ── Round-trip integration ────────────────────────────────────────────────────

@pytest.mark.integration
class TestUpstreamToDownstreamRoundTrip:
    """Full upstream→downstream round-trip integration tests."""

    def test_round_trip_produces_valid_research_brief(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        is_valid, errors = validate_research_brief(
            result["brief"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"ResearchBrief contract errors: {errors}"

    def test_round_trip_produces_valid_run_manifest(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        is_valid, errors = validate_run_manifest(
            result["run_manifest"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"RunManifest contract errors: {errors}"

    def test_round_trip_output_files_exist(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

    def test_round_trip_brief_on_disk_valid(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        with open(result["brief_path"]) as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"On-disk ResearchBrief errors: {errors}"

    def test_round_trip_with_downstream_handoff_manifest(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(tmp_path),
            upstream_source_run_id=fixtures.graph.source_run_id if fixtures.graph else None,
        )
        assert Path(hm_result["handoff_manifest_path"]).exists()
        with open(hm_result["handoff_manifest_path"]) as f:
            hm = json.load(f)
        assert hm["handoff_type"] == "downstream"
        assert hm["produced_for"] == "media-generation-pipeline"

    def test_round_trip_upstream_provenance_in_run_manifest(self, tmp_path):
        """RunManifest.inputs.upstream_provenance should trace back to material-ingestion."""
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        manifest = result["run_manifest"]
        prov = manifest.inputs.get("upstream_provenance", {})
        assert prov.get("graph_producer") == "material-ingestion-pipeline"
        assert prov.get("graph_source_run_id") == "ingest-run-001"

    def test_round_trip_source_count(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        assert len(brief.source_index) == 6

    def test_round_trip_entity_count(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        assert len(brief.entities) == 5

    def test_round_trip_finding_count(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        assert len(brief.key_findings) == 9

    def test_round_trip_topic_preserved(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        brief = result["brief"]
        assert "James Webb" in brief.topic

    def test_round_trip_source_attribution_present(self, tmp_path):
        """Each source_index entry should have non-empty source_id and title."""
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        for src in result["brief"].source_index:
            assert src.source_id
            assert src.title


# ── Canonical downstream fixtures ────────────────────────────────────────────

class TestCanonicalDownstreamFixtures:
    """Validate pre-generated canonical downstream fixtures in integration_fixtures/."""

    def test_downstream_research_brief_exists(self):
        assert (DOWNSTREAM_DIR / "ResearchBrief.json").exists()

    def test_downstream_run_manifest_exists(self):
        assert (DOWNSTREAM_DIR / "RunManifest.json").exists()

    def test_downstream_handoff_manifest_exists(self):
        assert (DOWNSTREAM_DIR / "handoff_manifest.json").exists()

    def test_downstream_research_brief_contract_valid(self):
        with open(DOWNSTREAM_DIR / "ResearchBrief.json") as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Canonical ResearchBrief errors: {errors}"

    def test_downstream_run_manifest_contract_valid(self):
        with open(DOWNSTREAM_DIR / "RunManifest.json") as f:
            data = json.load(f)
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Canonical RunManifest errors: {errors}"

    def test_downstream_handoff_manifest_schema_fields(self):
        with open(DOWNSTREAM_DIR / "handoff_manifest.json") as f:
            hm = json.load(f)
        assert hm["schema_version"] == "1.0.0"
        assert hm["handoff_type"] == "downstream"
        assert hm["pipeline"] == "content-research-pipeline"
        assert hm["produced_for"] == "media-generation-pipeline"
        assert "topic" in hm
        assert "source_run_id" in hm
        assert "artifacts" in hm
        assert "regeneration_command" in hm
        assert "validation_command" in hm
        assert "known_limitations" in hm

    def test_downstream_handoff_manifest_artifact_paths_exist(self):
        with open(DOWNSTREAM_DIR / "handoff_manifest.json") as f:
            hm = json.load(f)
        for artifact in hm["artifacts"]:
            path = DOWNSTREAM_DIR / artifact["path"]
            assert path.exists(), (
                f"Artifact path declared in handoff_manifest does not exist: {path}"
            )

    def test_downstream_handoff_manifest_has_upstream_source_run_id(self):
        with open(DOWNSTREAM_DIR / "handoff_manifest.json") as f:
            hm = json.load(f)
        assert hm.get("upstream_source_run_id") == "ingest-run-001"

    def test_downstream_research_brief_producer(self):
        with open(DOWNSTREAM_DIR / "ResearchBrief.json") as f:
            data = json.load(f)
        assert data["producer"] == "content-research-pipeline"

    def test_downstream_run_manifest_producer(self):
        with open(DOWNSTREAM_DIR / "RunManifest.json") as f:
            data = json.load(f)
        assert data["producer"] == "content-research-pipeline"

    def test_downstream_run_manifest_inputs_have_upstream_provenance(self):
        with open(DOWNSTREAM_DIR / "RunManifest.json") as f:
            data = json.load(f)
        prov = data["inputs"].get("upstream_provenance", {})
        assert prov.get("graph_producer") == "material-ingestion-pipeline"

    def test_upstream_and_downstream_topic_match(self):
        with open(UPSTREAM_DIR / "handoff_manifest.json") as f:
            up = json.load(f)
        with open(DOWNSTREAM_DIR / "handoff_manifest.json") as f:
            down = json.load(f)
        assert up["topic"] == down["topic"]

    def test_downstream_handoff_manifest_research_brief_required(self):
        with open(DOWNSTREAM_DIR / "handoff_manifest.json") as f:
            hm = json.load(f)
        rb = next(a for a in hm["artifacts"] if a["artifact_type"] == "ResearchBrief")
        assert rb["required"] is True
