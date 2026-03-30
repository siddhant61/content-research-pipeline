"""
Tests for the contract validator utility.
"""

import json
import pytest
from pathlib import Path

from src.content_research_pipeline.utils.contract_validator import (
    validate_brief_file,
    validate_manifest_file,
    validate_required_fields,
    validate_research_brief,
    validate_run_manifest,
)


CONTRACT_PATH = str(
    Path(__file__).parent.parent / "contracts" / "shared_artifacts.json"
)


class TestValidateRequiredFields:
    """Test required field validation."""

    def test_valid_research_brief(self):
        data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "topic": "test",
            "research_question": "test?",
            "executive_summary": "summary",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        is_valid, missing = validate_required_fields(
            data, "ResearchBrief", CONTRACT_PATH
        )
        assert is_valid
        assert missing == []

    def test_missing_fields(self):
        data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
        }
        is_valid, missing = validate_required_fields(
            data, "ResearchBrief", CONTRACT_PATH
        )
        assert not is_valid
        assert "topic" in missing
        assert "executive_summary" in missing

    def test_unknown_artifact_type(self):
        is_valid, errors = validate_required_fields(
            {}, "UnknownType", CONTRACT_PATH
        )
        assert not is_valid
        assert any("Unknown artifact type" in e for e in errors)


class TestValidateResearchBrief:
    """Test ResearchBrief validation."""

    def test_valid_brief(self):
        data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "topic": "test",
            "research_question": "test?",
            "executive_summary": "summary",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert is_valid
        assert errors == []

    def test_wrong_artifact_type(self):
        data = {
            "artifact_type": "RunManifest",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "topic": "test",
            "research_question": "test?",
            "executive_summary": "summary",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert not is_valid
        assert any("artifact_type must be 'ResearchBrief'" in e for e in errors)

    def test_list_field_type_check(self):
        data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "topic": "test",
            "research_question": "test?",
            "executive_summary": "summary",
            "key_findings": "not a list",
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert not is_valid
        assert any("key_findings" in e and "must be a list" in e for e in errors)

    def test_citation_map_type_check(self):
        data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "topic": "test",
            "research_question": "test?",
            "executive_summary": "summary",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": "not a dict",
            "open_questions": [],
            "recommended_angles": [],
        }
        is_valid, errors = validate_research_brief(data, CONTRACT_PATH)
        assert not is_valid
        assert any("citation_map" in e and "must be a dict" in e for e in errors)


class TestValidateRunManifest:
    """Test RunManifest validation."""

    def test_valid_manifest(self):
        data = {
            "artifact_type": "RunManifest",
            "schema_version": "1.0.0",
            "artifact_id": "manifest-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "pipeline_name": "content-research-pipeline",
            "pipeline_stage": "generate-brief",
            "status": "completed",
            "inputs": {},
            "outputs": [],
            "metrics": {},
            "errors": [],
        }
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert is_valid
        assert errors == []

    def test_missing_pipeline_name(self):
        data = {
            "artifact_type": "RunManifest",
            "schema_version": "1.0.0",
            "artifact_id": "manifest-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
        }
        is_valid, errors = validate_run_manifest(data, CONTRACT_PATH)
        assert not is_valid
        assert any("pipeline_name" in e for e in errors)


class TestValidateBriefFile:
    """Test file-level validation."""

    def test_valid_file(self, tmp_path):
        data = {
            "artifact_type": "ResearchBrief",
            "schema_version": "1.0.0",
            "artifact_id": "brief-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "topic": "test",
            "research_question": "test?",
            "executive_summary": "summary",
            "key_findings": [],
            "entities": [],
            "timeline": [],
            "source_index": [],
            "citation_map": {},
            "open_questions": [],
            "recommended_angles": [],
        }
        path = tmp_path / "brief.json"
        path.write_text(json.dumps(data))

        is_valid, errors = validate_brief_file(str(path), CONTRACT_PATH)
        assert is_valid

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json {{{")

        is_valid, errors = validate_brief_file(str(path), CONTRACT_PATH)
        assert not is_valid
        assert any("Invalid JSON" in e for e in errors)

    def test_missing_file(self):
        is_valid, errors = validate_brief_file("/nonexistent.json", CONTRACT_PATH)
        assert not is_valid
        assert any("File not found" in e for e in errors)


class TestValidateManifestFile:
    """Test RunManifest file validation."""

    def test_valid_file(self, tmp_path):
        data = {
            "artifact_type": "RunManifest",
            "schema_version": "1.0.0",
            "artifact_id": "manifest-001",
            "created_at": "2026-01-01T00:00:00Z",
            "producer": "test",
            "source_run_id": "run-001",
            "pipeline_name": "content-research-pipeline",
            "pipeline_stage": "test",
            "status": "completed",
            "inputs": {},
            "outputs": [],
            "metrics": {},
            "errors": [],
        }
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(data))

        is_valid, errors = validate_manifest_file(str(path), CONTRACT_PATH)
        assert is_valid
