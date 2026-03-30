"""
Contract validation utilities for the Content Research Pipeline.

Validates that generated artifacts conform to the shared artifact contract
defined in contracts/shared_artifacts.json.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..data.artifacts import ResearchBrief, RunManifest


def _load_contract(contract_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the shared artifact contract JSON."""
    if contract_path is None:
        # Default to the contracts directory relative to the repo root
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        contract_path = str(repo_root / "contracts" / "shared_artifacts.json")
    with open(contract_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_required_fields(
    data: Dict[str, Any],
    artifact_type: str,
    contract_path: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate that a dict has all required fields for the given artifact type.

    Args:
        data: The artifact data as a dict.
        artifact_type: The artifact type name (e.g. 'ResearchBrief').
        contract_path: Optional path to the contract JSON.

    Returns:
        Tuple of (is_valid, list of missing field names).
    """
    contract = _load_contract(contract_path)
    artifacts = contract.get("artifacts", {})

    if artifact_type not in artifacts:
        return False, [f"Unknown artifact type: {artifact_type}"]

    required = artifacts[artifact_type].get("required_fields", [])
    missing = [field for field in required if field not in data]

    return len(missing) == 0, missing


def validate_research_brief(
    data: Dict[str, Any],
    contract_path: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate a ResearchBrief dict against the shared contract.

    Checks:
        1. All required fields are present.
        2. artifact_type is 'ResearchBrief'.
        3. schema_version is present.
        4. Key list fields are lists (not null).

    Args:
        data: The ResearchBrief as a dict.
        contract_path: Optional path to the contract JSON.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: List[str] = []

    # Check artifact_type
    if data.get("artifact_type") != "ResearchBrief":
        errors.append(
            f"artifact_type must be 'ResearchBrief', got '{data.get('artifact_type')}'"
        )

    # Check required fields
    is_valid, missing = validate_required_fields(
        data, "ResearchBrief", contract_path
    )
    if not is_valid:
        errors.extend([f"Missing required field: {f}" for f in missing])

    # Check list fields are actually lists
    list_fields = [
        "key_findings", "entities", "timeline",
        "source_index", "open_questions", "recommended_angles",
    ]
    for field in list_fields:
        val = data.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"Field '{field}' must be a list, got {type(val).__name__}")

    # citation_map should be a dict
    cm = data.get("citation_map")
    if cm is not None and not isinstance(cm, dict):
        errors.append(f"Field 'citation_map' must be a dict, got {type(cm).__name__}")

    return len(errors) == 0, errors


def validate_run_manifest(
    data: Dict[str, Any],
    contract_path: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Validate a RunManifest dict against the shared contract.

    Args:
        data: The RunManifest as a dict.
        contract_path: Optional path to the contract JSON.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: List[str] = []

    if data.get("artifact_type") != "RunManifest":
        errors.append(
            f"artifact_type must be 'RunManifest', got '{data.get('artifact_type')}'"
        )

    is_valid, missing = validate_required_fields(
        data, "RunManifest", contract_path
    )
    if not is_valid:
        errors.extend([f"Missing required field: {f}" for f in missing])

    return len(errors) == 0, errors


def validate_brief_file(
    path: str,
    contract_path: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Load a ResearchBrief JSON file and validate it.

    Args:
        path: Path to the JSON file.
        contract_path: Optional path to the contract JSON.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return False, [f"File not found: {path}"]

    return validate_research_brief(data, contract_path)


def validate_manifest_file(
    path: str,
    contract_path: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Load a RunManifest JSON file and validate it.

    Args:
        path: Path to the JSON file.
        contract_path: Optional path to the contract JSON.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return False, [f"File not found: {path}"]

    return validate_run_manifest(data, contract_path)
