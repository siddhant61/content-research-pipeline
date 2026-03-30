"""
Tests that validate demo sample artifacts against the shared contract.

These tests ensure that the sample/scaffold artifacts in demo_data/
conform to the shared_artifacts.json contract, catching any drift
between the contract and the demo data.
"""

import json
import pytest
from pathlib import Path

from src.content_research_pipeline.utils.contract_validator import (
    validate_required_fields,
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


def _load_contract():
    with open(CONTRACT_PATH) as f:
        return json.load(f)


class TestDemoManifestContract:
    """Validate the demo RawSourceBundle manifest against the contract."""

    def test_manifest_has_all_required_fields(self):
        with open(DEMO_DIR / "manifest.json") as f:
            data = json.load(f)
        is_valid, missing = validate_required_fields(
            data, "RawSourceBundle", CONTRACT_PATH
        )
        assert is_valid, f"Missing required fields: {missing}"

    def test_manifest_artifact_type(self):
        with open(DEMO_DIR / "manifest.json") as f:
            data = json.load(f)
        assert data["artifact_type"] == "RawSourceBundle"

    def test_manifest_schema_version(self):
        with open(DEMO_DIR / "manifest.json") as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0.0"

    def test_manifest_sources_have_required_fields(self):
        contract = _load_contract()
        source_required = contract["artifacts"]["RawSourceBundle"]["source_item_required_fields"]
        with open(DEMO_DIR / "manifest.json") as f:
            data = json.load(f)
        for i, source in enumerate(data["sources"]):
            missing = [f for f in source_required if f not in source]
            assert not missing, (
                f"Source [{i}] ({source.get('source_id', '?')}) "
                f"missing required fields: {missing}"
            )

    def test_manifest_has_sources(self):
        with open(DEMO_DIR / "manifest.json") as f:
            data = json.load(f)
        assert len(data["sources"]) > 0, "Manifest must have at least one source"

    def test_manifest_topic_matches_demo_name(self):
        with open(DEMO_DIR / "manifest.json") as f:
            data = json.load(f)
        assert "jwst" in data["topic"].lower() or "webb" in data["topic"].lower()


class TestDemoResearchBriefSample:
    """Validate the demo ResearchBrief sample against the contract."""

    def test_sample_brief_has_all_required_fields(self):
        with open(DEMO_DIR / "ResearchBrief.sample.json") as f:
            data = json.load(f)
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid, f"Validation errors: {errors}"

    def test_sample_brief_artifact_type(self):
        with open(DEMO_DIR / "ResearchBrief.sample.json") as f:
            data = json.load(f)
        assert data["artifact_type"] == "ResearchBrief"

    def test_sample_brief_schema_version(self):
        with open(DEMO_DIR / "ResearchBrief.sample.json") as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0.0"


class TestDemoRunManifestSample:
    """Validate the demo RunManifest sample against the contract."""

    def test_sample_manifest_has_all_required_fields(self):
        with open(DEMO_DIR / "RunManifest.sample.json") as f:
            data = json.load(f)
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid, f"Validation errors: {errors}"

    def test_sample_manifest_artifact_type(self):
        with open(DEMO_DIR / "RunManifest.sample.json") as f:
            data = json.load(f)
        assert data["artifact_type"] == "RunManifest"

    def test_sample_manifest_schema_version(self):
        with open(DEMO_DIR / "RunManifest.sample.json") as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0.0"
