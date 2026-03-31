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
        # Verify the loaded graph data matches the source file
        with open(UPSTREAM_DIR / "KnowledgeGraphPackage.json") as f:
            expected = json.load(f)
        assert fixtures.graph.artifact_id == expected["artifact_id"]
        assert fixtures.graph.topic == expected["topic"]


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
        assert "resolve_upstream" in self.workflow_text

    def test_fixture_fallback_path_in_resolve(self):
        assert "integration_fixtures/jwst/upstream/" in self.workflow_text

    def test_upstream_dir_output_used_in_generate(self):
        assert "steps.resolve_upstream.outputs.upstream_dir" in self.workflow_text

    def test_upload_artifact_step_present(self):
        assert "actions/upload-artifact@v4" in self.workflow_text

    def test_handoff_manifest_check_in_resolve(self):
        assert "handoff_manifest.json" in self.workflow_text


# ── Diagnostic hardening (Phase 4.1) ────────────────────────────────────────

class TestWorkflowDiagnosticHardening:
    """Validate that the reusable workflow includes diagnostic and error-handling
    improvements for artifact transport (Phase 4.1 hardening)."""

    @pytest.fixture(autouse=True)
    def _load_workflow(self):
        self.workflow_text = WORKFLOW_PATH.read_text()

    def test_debug_step_present(self):
        """A dedicated debug step must exist to print artifact transport inputs."""
        assert "Debug artifact transport inputs" in self.workflow_text

    def test_debug_step_prints_upstream_artifact_name(self):
        """The debug step must reference upstream_artifact_name."""
        assert "upstream_artifact_name received:" in self.workflow_text

    def test_debug_step_prints_download_directory(self):
        """The debug step must print the download target directory."""
        assert "/tmp/upstream-handoff" in self.workflow_text

    def test_download_step_has_continue_on_error(self):
        """The download step must use continue-on-error so failures are diagnosable."""
        assert "continue-on-error: true" in self.workflow_text

    def test_download_step_has_id(self):
        """The download step must have an id to reference its outcome."""
        assert "id: download-artifact" in self.workflow_text

    def test_resolve_step_verifies_download(self):
        """The resolve step must verify the download outcome."""
        assert "Verify artifact download" in self.workflow_text or \
            "steps.download-artifact.outcome" in self.workflow_text

    def test_verify_step_checks_outcome(self):
        """The verification step must check the download step outcome."""
        assert "steps.download-artifact.outcome" in self.workflow_text

    def test_verify_step_emits_error_on_failure(self):
        """The verification step must emit a clear ::error annotation on failure."""
        assert "::error ::Artifact download FAILED" in self.workflow_text

    def test_resolve_step_logs_both_paths(self):
        """The resolve step must log both the artifact and fallback paths."""
        assert "Artifact download path:" in self.workflow_text
        assert "Fallback fixture path:" in self.workflow_text

    def test_workflow_dispatch_unchanged(self):
        """workflow_dispatch must remain a bare trigger with no inputs."""
        import yaml
        wf = yaml.safe_load(self.workflow_text)
        # PyYAML parses the 'on' key as boolean True
        triggers = wf.get("on") or wf.get(True)
        assert triggers is not None, "Workflow must have an 'on' trigger block"
        dispatch = triggers.get("workflow_dispatch")
        assert dispatch is None or dispatch == {}, (
            f"workflow_dispatch should be bare, got: {dispatch}"
        )


# ── Nested artifact directory resolution (Phase 4.1 fix) ────────────────────

class TestNestedArtifactDirectoryResolution:
    """Validate that the workflow robustly handles both direct and nested
    artifact extraction layouts from actions/download-artifact."""

    @pytest.fixture(autouse=True)
    def _load_workflow(self):
        self.workflow_text = WORKFLOW_PATH.read_text()

    def test_post_download_debug_step_present(self):
        """A debug step after download must inspect the downloaded layout."""
        assert "Debug downloaded artifact layout" in self.workflow_text

    def test_post_download_debug_runs_ls_recursive(self):
        """The post-download debug step must run ls -R on the download path."""
        assert "ls -R /tmp/upstream-handoff" in self.workflow_text

    def test_post_download_debug_prints_artifact_name(self):
        """The post-download debug step must print the upstream_artifact_name."""
        assert "upstream_artifact_name:" in self.workflow_text

    def test_resolve_step_has_id(self):
        """The resolve step must have an id to set outputs."""
        assert "id: resolve_upstream" in self.workflow_text

    def test_verify_checks_root_first(self):
        """Verify step must first check for handoff_manifest.json at root."""
        assert "handoff_manifest.json found directly" in self.workflow_text

    def test_verify_checks_nested_subdirectory(self):
        """Verify step must check for handoff_manifest.json in child directories."""
        assert "nested subdirectory layout" in self.workflow_text

    def test_resolve_sets_upstream_dir_output(self):
        """Resolve step must set upstream_dir as a step output."""
        assert "upstream_dir=" in self.workflow_text

    def test_generate_uses_resolve_upstream_output(self):
        """Generate step must reference the resolve_upstream step output."""
        assert "steps.resolve_upstream.outputs.upstream_dir" in self.workflow_text

    def test_error_includes_directory_tree(self):
        """Error paths must include 'Directory tree:' for debugging."""
        assert "Directory tree:" in self.workflow_text

    def test_error_on_missing_manifest_mentions_child_dirs(self):
        """Error message must mention both root and child directories were checked."""
        assert "checked root and all child directories" in self.workflow_text

    def test_error_on_multiple_nested_dirs(self):
        """Workflow must error if multiple child dirs contain handoff_manifest.json."""
        assert "Multiple nested directories" in self.workflow_text


class TestNestedLayoutPythonLoading:
    """Verify that load_from_handoff_manifest works when the upstream
    artifacts live inside a nested subdirectory (simulating the layout
    produced when download-artifact nests under a child directory)."""

    def test_load_from_nested_subdirectory(self, tmp_path):
        """Simulate nested layout: /tmp/upstream-handoff/jwst-upstream-handoff/..."""
        outer = tmp_path / "upstream-handoff"
        nested = outer / "jwst-upstream-handoff"
        _copy_upstream_to(nested)
        # The Python loader should work when pointed at the nested dir
        fixtures = load_from_handoff_manifest(str(nested))
        assert fixtures.has_any
        assert fixtures.graph is not None
        assert fixtures.handoff_source_run_id == "fixture-jwst-001"

    def test_nested_paths_reference_nested_dir(self, tmp_path):
        """Artifact paths should reference the nested directory."""
        outer = tmp_path / "upstream-handoff"
        nested = outer / "jwst-upstream-handoff"
        _copy_upstream_to(nested)
        fixtures = load_from_handoff_manifest(str(nested))
        for attr in ("graph_path", "documents_path", "chunks_path", "bundle_path"):
            path_val = getattr(fixtures, attr)
            assert path_val is not None
            assert str(nested) in path_val

    def test_nested_brief_generation(self, tmp_path):
        """Full brief generation from a nested directory should succeed."""
        outer = tmp_path / "upstream-handoff"
        nested = outer / "jwst-upstream-handoff"
        _copy_upstream_to(nested)
        fixtures = load_from_handoff_manifest(str(nested))
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        result = generate_brief_from_fixtures(fixtures, output_dir=str(out_dir))
        assert Path(result["brief_path"]).exists()
        assert Path(result["manifest_path"]).exists()
        is_valid, errors = validate_research_brief(
            result["brief"].model_dump(), CONTRACT_PATH
        )
        assert is_valid, f"ResearchBrief contract errors: {errors}"

    def test_outer_dir_without_manifest_falls_back(self, tmp_path):
        """Loading from the outer directory (no handoff_manifest.json at root)
        should fall back to auto-discovery, which finds nothing since the
        artifacts are in the nested subdirectory."""
        outer = tmp_path / "upstream-handoff"
        nested = outer / "jwst-upstream-handoff"
        _copy_upstream_to(nested)
        # The outer dir has no handoff_manifest.json and no well-known filenames
        fixtures = load_from_handoff_manifest(str(outer))
        # Auto-discovery won't find artifacts because they're inside a subdir
        # that doesn't match the well-known filenames
        assert fixtures.graph is None
        assert fixtures.documents is None
        assert fixtures.handoff_source_run_id is None
