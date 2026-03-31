"""
Phase 4 tests: upstream artifact transport for reusable workflow mode.

Phase 4 adds support for consuming the actual upstream handoff artifact
produced by an earlier job in the same orchestration run (downloaded via
``actions/download-artifact``), rather than relying exclusively on the
committed local fixture directory.

Test categories
---------------
* Path resolution — correct upstream directory is selected based on available
  inputs (downloaded artifact vs. committed fixtures).
* Source-run-id preservation — the ``source_run_id`` from a downloaded
  artifact directory is correctly propagated through the downstream outputs.
* Arbitrary-directory loading — ``load_from_handoff_manifest`` works from
  any directory (simulating a download path like ``/tmp/upstream-handoff``).
* Fallback behaviour — when no downloaded artifact is present the pipeline
  correctly falls back to the local fixture directory.
* Workflow YAML structure — the reusable workflow declares the expected
  ``workflow_call`` inputs.

Contract assumptions
--------------------
* integration_fixtures/jwst/upstream/ is the committed fixture directory.
* A downloaded artifact directory has the same internal structure (a
  ``handoff_manifest.json`` plus the declared artifact files).
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
    generate_brief_from_fixtures,
    generate_downstream_handoff_manifest,
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
WORKFLOW_PATH = (
    Path(__file__).parent.parent
    / ".github"
    / "workflows"
    / "manual-build-downstream.yml"
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _copy_upstream_to(dest: Path) -> Path:
    """Copy the canonical upstream fixture directory to *dest* and return it."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(UPSTREAM_DIR, dest)
    return dest


def _make_upstream_with_run_id(dest: Path, source_run_id: str) -> Path:
    """Copy the upstream fixtures and rewrite source_run_id everywhere."""
    _copy_upstream_to(dest)
    # Rewrite the handoff manifest
    hm_path = dest / "handoff_manifest.json"
    hm = json.loads(hm_path.read_text())
    hm["source_run_id"] = source_run_id
    hm_path.write_text(json.dumps(hm, indent=2))
    # Rewrite each artifact file
    for artifact in hm["artifacts"]:
        fpath = dest / artifact["path"]
        if fpath.exists():
            data = json.loads(fpath.read_text())
            if "source_run_id" in data:
                data["source_run_id"] = source_run_id
            fpath.write_text(json.dumps(data, indent=2))
    return dest


# ── Arbitrary-directory loading (simulated artifact download) ────────────────

class TestArtifactDirectoryLoading:
    """load_from_handoff_manifest works from any directory, not just the
    committed fixture path — simulating a downloaded artifact."""

    def test_load_from_arbitrary_path(self, tmp_path):
        artifact_dir = _copy_upstream_to(tmp_path / "upstream-handoff")
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        assert fixtures.has_any
        assert fixtures.graph is not None
        assert fixtures.documents is not None
        assert fixtures.chunks is not None
        assert fixtures.bundle is not None

    def test_fixture_dir_reflects_download_path(self, tmp_path):
        artifact_dir = _copy_upstream_to(tmp_path / "upstream-handoff")
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        assert str(artifact_dir) in fixtures.fixture_dir

    def test_artifact_paths_point_into_download_dir(self, tmp_path):
        artifact_dir = _copy_upstream_to(tmp_path / "upstream-handoff")
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        for attr in ("graph_path", "documents_path", "chunks_path", "bundle_path"):
            path_val = getattr(fixtures, attr)
            assert path_val is not None, f"{attr} should not be None"
            assert str(artifact_dir) in path_val, (
                f"{attr} should reference the download dir, got: {path_val}"
            )

    def test_handoff_source_run_id_from_download_dir(self, tmp_path):
        artifact_dir = _copy_upstream_to(tmp_path / "upstream-handoff")
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        assert fixtures.handoff_source_run_id == "fixture-jwst-001"


# ── Source-run-id preservation through the full pipeline ─────────────────────

class TestArtifactTransportSourceRunId:
    """Verify that a non-default source_run_id from a downloaded artifact
    is correctly propagated through brief generation and downstream handoff."""

    LIVE_RUN_ID = "orchestration-run-42abc"

    def test_custom_source_run_id_loaded(self, tmp_path):
        artifact_dir = _make_upstream_with_run_id(
            tmp_path / "upstream", self.LIVE_RUN_ID
        )
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        assert fixtures.handoff_source_run_id == self.LIVE_RUN_ID

    def test_custom_source_run_id_in_upstream_provenance(self, tmp_path):
        artifact_dir = _make_upstream_with_run_id(
            tmp_path / "upstream", self.LIVE_RUN_ID
        )
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = generate_brief_from_fixtures(fixtures, output_dir=str(out_dir))
        prov = result["run_manifest"].inputs.get("upstream_provenance", {})
        assert prov["graph_source_run_id"] == self.LIVE_RUN_ID

    def test_custom_source_run_id_in_downstream_handoff(self, tmp_path):
        artifact_dir = _make_upstream_with_run_id(
            tmp_path / "upstream", self.LIVE_RUN_ID
        )
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = generate_brief_from_fixtures(fixtures, output_dir=str(out_dir))
        hm_result = generate_downstream_handoff_manifest(
            brief=result["brief"],
            run_manifest=result["run_manifest"],
            brief_path=result["brief_path"],
            run_manifest_path=result["manifest_path"],
            output_dir=str(out_dir),
            upstream_source_run_id=fixtures.handoff_source_run_id,
        )
        assert (
            hm_result["handoff_manifest"]["upstream_source_run_id"]
            == self.LIVE_RUN_ID
        )

    def test_brief_contract_valid_with_custom_run_id(self, tmp_path):
        artifact_dir = _make_upstream_with_run_id(
            tmp_path / "upstream", self.LIVE_RUN_ID
        )
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = generate_brief_from_fixtures(fixtures, output_dir=str(out_dir))
        is_valid, errors = validate_research_brief(
            result["brief"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"ResearchBrief contract errors: {errors}"

    def test_run_manifest_contract_valid_with_custom_run_id(self, tmp_path):
        artifact_dir = _make_upstream_with_run_id(
            tmp_path / "upstream", self.LIVE_RUN_ID
        )
        fixtures = load_from_handoff_manifest(str(artifact_dir))
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = generate_brief_from_fixtures(fixtures, output_dir=str(out_dir))
        is_valid, errors = validate_run_manifest(
            result["run_manifest"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"RunManifest contract errors: {errors}"


# ── Fallback to local fixtures ───────────────────────────────────────────────

class TestLocalFixtureFallback:
    """When no downloaded artifact is available, the pipeline should still
    work with committed local fixture directories."""

    def test_committed_upstream_dir_works(self):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        assert fixtures.has_any
        assert fixtures.handoff_source_run_id == "fixture-jwst-001"

    def test_committed_upstream_round_trip(self, tmp_path):
        fixtures = load_from_handoff_manifest(str(UPSTREAM_DIR))
        result = generate_brief_from_fixtures(fixtures, output_dir=str(tmp_path))
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()

    def test_auto_discovery_fallback_for_bare_dir(self, tmp_path):
        """A directory without handoff_manifest.json falls back to auto-discovery."""
        shutil.copy(
            UPSTREAM_DIR / "KnowledgeGraphPackage.json",
            tmp_path / "KnowledgeGraphPackage.json",
        )
        fixtures = load_from_handoff_manifest(str(tmp_path))
        assert fixtures.graph is not None
        assert fixtures.handoff_source_run_id is None


# ── Workflow YAML structure ──────────────────────────────────────────────────

class TestWorkflowYAMLStructure:
    """Validate the reusable workflow declares the expected inputs and steps."""

    @pytest.fixture(autouse=True)
    def _load_workflow(self):
        # Import yaml parser only if available; fall back to basic string checks.
        self.workflow_text = WORKFLOW_PATH.read_text()

    def test_workflow_call_trigger_present(self):
        assert "workflow_call:" in self.workflow_text

    def test_workflow_dispatch_trigger_present(self):
        assert "workflow_dispatch:" in self.workflow_text

    def test_upstream_artifact_name_input_declared(self):
        assert "upstream_artifact_name:" in self.workflow_text

    def test_download_artifact_step_present(self):
        assert "actions/download-artifact@v4" in self.workflow_text

    def test_download_is_conditional(self):
        assert "inputs.upstream_artifact_name" in self.workflow_text

    def test_resolve_upstream_step_present(self):
        assert "resolve-upstream" in self.workflow_text

    def test_fixture_fallback_path_in_resolve(self):
        assert "integration_fixtures/jwst/upstream/" in self.workflow_text

    def test_upstream_dir_output_used_in_generate(self):
        assert "steps.resolve-upstream.outputs.upstream_dir" in self.workflow_text

    def test_upload_artifact_step_present(self):
        assert "actions/upload-artifact@v4" in self.workflow_text

    def test_handoff_manifest_check_in_resolve(self):
        assert "handoff_manifest.json" in self.workflow_text
