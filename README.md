# Content Research Pipeline

**Research and enrichment layer** of a 3-part AI workflow stack.

This repository consumes structured upstream artifacts from the [material-ingestion-pipeline](https://github.com/siddhant61/material-ingestion-pipeline) and produces a contract-compliant **ResearchBrief** for downstream [media-generation-pipeline](https://github.com/siddhant61/media-generation-pipeline).

## Cross-Repo Architecture

```
material-ingestion-pipeline          content-research-pipeline          media-generation-pipeline
────────────────────────────         ─────────────────────────          ──────────────────────────
RawSourceBundle ──────────────┐
NormalizedDocumentSet ────────┤
ChunkSet ─────────────────────┼──▶  ResearchBrief ──────────────────▶  ScenePlan
KnowledgeGraphPackage ────────┘     RunManifest                        MediaPackage
```

### Shared Contracts

All three repos share a versioned artifact contract:
- **Contract definition**: `contracts/shared_artifacts.json` (v1.0.0)
- **Schema documentation**: `contracts/schemas.md`
- **Demo manifest**: `contracts/demo_manifest.md`

## Phase 3 — Canonical Upstream/Downstream Handoff Integration

Phase 3 makes this repo the authoritative middle transformer in the 3-pipeline chain.
It consumes the canonical upstream handoff package from `material-ingestion-pipeline`
(declared by a `handoff_manifest.json`) and emits the canonical downstream handoff
package for `media-generation-pipeline`.

### Integration Fixtures

Canonical, stable handoff packages live under `integration_fixtures/jwst/`:

```
integration_fixtures/
└── jwst/
    ├── upstream/                          # Canonical upstream package (owned by material-ingestion)
    │   ├── handoff_manifest.json          # Declares artifacts and regeneration commands
    │   ├── KnowledgeGraphPackage.json     # KG (5 nodes, 4 edges)
    │   ├── NormalizedDocumentSet.json     # 2 normalized documents
    │   ├── ChunkSet.json                  # 6 text chunks
    │   └── RawSourceBundle.json           # 6 source references
    └── downstream/                        # Canonical downstream package (owned by this repo)
        ├── handoff_manifest.json          # Declares outputs for media-generation
        ├── ResearchBrief.json             # Synthesized research brief
        └── RunManifest.json               # Provenance and metrics
```

### Consuming the Upstream Handoff Package (Phase 3 Path)

```python
from content_research_pipeline.core.fixture_loader import load_from_handoff_manifest
from content_research_pipeline.core.brief_generator import (
    generate_brief_from_fixtures,
    generate_downstream_handoff_manifest,
)

# Load upstream handoff package (reads handoff_manifest.json)
fixtures = load_from_handoff_manifest("integration_fixtures/jwst/upstream/")

# Generate contract-valid ResearchBrief + RunManifest
result = generate_brief_from_fixtures(fixtures, output_dir="output/")

# Emit downstream handoff manifest for media-generation
handoff = generate_downstream_handoff_manifest(
    brief=result["brief"],
    run_manifest=result["run_manifest"],
    brief_path=result["brief_path"],
    run_manifest_path=result["manifest_path"],
    output_dir="output/",
    upstream_source_run_id=fixtures.graph.source_run_id,
)
print(handoff["handoff_manifest_path"])   # output/handoff_manifest.json
```

### CLI — Phase 3 Canonical Integration Command

```bash
# Consume upstream handoff package and emit downstream package
PYTHONPATH=src python -m content_research_pipeline.brief_cli generate \
    --upstream-handoff-dir integration_fixtures/jwst/upstream/ \
    --output-dir /tmp/jwst_downstream/ \
    --emit-handoff-manifest
```

### Validate Canonical Downstream Fixtures

```bash
PYTHONPATH=src python -m content_research_pipeline.brief_cli validate \
    --brief integration_fixtures/jwst/downstream/ResearchBrief.json

PYTHONPATH=src python -m content_research_pipeline.brief_cli validate \
    --run-manifest integration_fixtures/jwst/downstream/RunManifest.json
```

### GitHub Actions — Downstream Handoff Build

The **Build Downstream Handoff** workflow (`.github/workflows/manual-build-downstream.yml`) regenerates the canonical downstream handoff package. It supports two modes of operation: a **manual local-fixture mode** and an **orchestration artifact-download mode**.

**Trigger modes:**

| Mode | Trigger | Use case |
|------|---------|----------|
| Manual (local fixture) | `workflow_dispatch` | Run from the **Actions** tab — uses committed `integration_fixtures/jwst/upstream/` |
| Orchestration (artifact download) | `workflow_call` with `upstream_artifact_name` | Called by an orchestration repo — downloads the real upstream artifact from the current run |

#### Manual Local-Fixture Mode

Uses the committed fixture directory `integration_fixtures/jwst/upstream/` as the upstream input. No additional inputs required.

**How to run:**
1. Go to the **Actions** tab in GitHub.
2. Select the **Build Downstream Handoff** workflow from the left sidebar.
3. Click **Run workflow** and confirm.

#### Orchestration Artifact-Download Mode

When called as a reusable workflow by an orchestrator (e.g. `pipeline-integration`), the workflow can download the actual upstream handoff artifact produced by an earlier job in the same orchestration run.

**`workflow_call` inputs:**

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `upstream_artifact_name` | `string` | no | `""` | Name of the upstream artifact to download via `actions/download-artifact`. When empty, falls back to local fixtures. |

The workflow resolves the upstream directory as follows:
1. If `upstream_artifact_name` is provided, download the named artifact into `/tmp/upstream-handoff`.
2. Check for `handoff_manifest.json` directly in `/tmp/upstream-handoff/` (direct layout).
3. If not found at root, check whether exactly one child directory contains `handoff_manifest.json` (nested layout) and use that directory instead.
4. If no valid handoff package is found in either layout, the workflow fails with a clear error and prints the full directory tree for debugging.
5. If `upstream_artifact_name` is not provided or empty, fall back to the committed `integration_fixtures/jwst/upstream/` directory.

**Supported artifact extraction layouts:**

`actions/download-artifact@v4` may produce either of these layouts depending on how the upstream artifact was uploaded:

```
# Layout A — Direct (files extracted at root)
/tmp/upstream-handoff/
├── handoff_manifest.json
├── KnowledgeGraphPackage.json
├── NormalizedDocumentSet.json
├── ChunkSet.json
└── RawSourceBundle.json

# Layout B — Nested (files inside a child directory)
/tmp/upstream-handoff/
└── jwst-upstream-handoff/
    ├── handoff_manifest.json
    ├── KnowledgeGraphPackage.json
    ├── NormalizedDocumentSet.json
    ├── ChunkSet.json
    └── RawSourceBundle.json
```

The workflow automatically detects and resolves both layouts.

The `source_run_id` from the downloaded artifact's `handoff_manifest.json` is preserved through the entire downstream output chain (ResearchBrief → RunManifest → downstream `handoff_manifest.json`).

**How to call as a reusable workflow (with upstream artifact):**
```yaml
jobs:
  ingest:
    # ... produces artifact "jwst-upstream-handoff"
  research:
    needs: ingest
    uses: siddhant61/content-research-pipeline/.github/workflows/manual-build-downstream.yml@main
    with:
      upstream_artifact_name: jwst-upstream-handoff
```

**How to call as a reusable workflow (local-fixture fallback):**
```yaml
jobs:
  research:
    uses: siddhant61/content-research-pipeline/.github/workflows/manual-build-downstream.yml@main
```

**Artifact output:**
- **Artifact name:** `jwst-downstream-handoff`
- **Output directory:** `integration_fixtures/jwst/downstream/`
- **Contents:** `ResearchBrief.json`, `RunManifest.json`, `handoff_manifest.json`

The workflow generates a fresh `ResearchBrief`, `RunManifest`, and `handoff_manifest.json` from the resolved upstream directory, validates each artifact against the shared contract, and uploads the complete downstream directory as the workflow artifact.

## Phase 2B — Full Upstream Handoff Integration

Phase 2B completes the upstream consumption path by adding ChunkSet support and
a canonical `generate_brief_from_fixtures()` entry-point for consuming a full
upstream handoff package.

### Upstream Files Expected

All upstream handoff artifacts live in a single directory.
The canonical demo directory is:

```
demo_data/jwst_star_formation_early_universe_demo/
```

| Filename | Artifact | Owner | Required? |
|----------|----------|-------|-----------|
| `manifest.json` | `RawSourceBundle` | material-ingestion-pipeline | Recommended (enriches citations) |
| `NormalizedDocumentSet.sample.json` | `NormalizedDocumentSet` | material-ingestion-pipeline | Recommended |
| `ChunkSet.sample.json` | `ChunkSet` | material-ingestion-pipeline | Optional (chunk-level provenance) |
| `KnowledgeGraphPackage.sample.json` | `KnowledgeGraphPackage` | material-ingestion-pipeline | Recommended (preferred input) |

At least one artifact must be present. When all four are provided, the
brief has the richest possible content and full provenance chain.

### Downstream Files Emitted

| Filename | Artifact | Owner | Location |
|----------|----------|-------|----------|
| `ResearchBrief.sample.json` | `ResearchBrief` | content-research-pipeline | `demo_data/jwst_star_formation_early_universe_demo/` |
| `RunManifest.sample.json` | `RunManifest` | content-research-pipeline | `demo_data/jwst_star_formation_early_universe_demo/` |

Runtime output follows the naming convention:
`<topic_slug>__<artifact_type>__<timestamp>.json` (written to `--output-dir`).

### Recommended Entry-Point (Phase 2B)

```python
from content_research_pipeline.core.fixture_loader import load_upstream_fixtures
from content_research_pipeline.core.brief_generator import generate_brief_from_fixtures

# Load all upstream artifacts from a handoff directory
fixtures = load_upstream_fixtures("demo_data/jwst_star_formation_early_universe_demo/")

# Generate a contract-valid ResearchBrief and RunManifest
result = generate_brief_from_fixtures(fixtures, output_dir="output/")

print(result["brief_path"])     # path to written ResearchBrief JSON
print(result["manifest_path"])  # path to written RunManifest JSON
```

### CLI (unchanged, --fixture-dir recommended)

```bash
# Phase 2B recommended: load all upstream artifacts from a handoff directory
python -m content_research_pipeline.brief_cli generate \
    --fixture-dir demo_data/jwst_star_formation_early_universe_demo/ \
    --output-dir output/
```

## Phase 2A — Upstream Fixture Consumption

Phase 2A adds a stable fixture-based integration path for consuming real
upstream artifacts from `material-ingestion-pipeline`.

### Fixture Directory Loading

The new `--fixture-dir` CLI option auto-discovers all upstream artifacts
in a directory using well-known filenames:

```bash
# Recommended: load all upstream artifacts from a fixture directory
python -m content_research_pipeline.brief_cli generate \
    --fixture-dir demo_data/jwst_star_formation_early_universe_demo/ \
    --output-dir output/
```

The loader looks for:
| Filename | Artifact |
|----------|----------|
| `KnowledgeGraphPackage.sample.json` or `KnowledgeGraphPackage.json` | KnowledgeGraphPackage |
| `NormalizedDocumentSet.sample.json` or `NormalizedDocumentSet.json` | NormalizedDocumentSet |
| `ChunkSet.sample.json` or `ChunkSet.json` | ChunkSet |
| `manifest.json` or `RawSourceBundle.json` | RawSourceBundle |

### Provenance Preservation

When upstream artifacts are consumed, the `RunManifest.inputs.upstream_provenance`
field captures:
- Producer pipeline name and run ID for each artifact (KG, NDS, ChunkSet, bundle)
- Full `provenance` dict from `KnowledgeGraphPackage` (pipeline, stage, source_artifact)

### Citation Enrichment

Source attribution is merged across all available artifacts.  When both a
`KnowledgeGraphPackage` and `RawSourceBundle` are provided:
- Source entries from the bundle provide rich metadata (org, URL, license)
- KG-only source entries are supplemented with bundle data where source_ids match

### Field Degradations (KG-Only Path)

When a `KnowledgeGraphPackage` is consumed without a `RawSourceBundle`:
| Field | Value | Reason |
|-------|-------|--------|
| `source_index[].origin_org` | `"unknown"` | KG source_refs lack org metadata |
| `source_index[].url` | `""` | KG source_refs lack URL metadata |
| `citation_map[].origin_org` | `"unknown"` | Same as above |
| `citation_map[].url` | `""` | Same as above |
| `citation_map[].license` | `"unknown"` | Same as above |

These degradations are fully resolved when a `RawSourceBundle` is also provided.

## Phase 1.5 — Upstream Artifact Consumption

The generator accepts any combination of upstream ingestion artifacts and applies
a priority-based fallback chain for content synthesis:

1. **KnowledgeGraphPackage** (preferred) — entities from nodes, findings from edges
2. **NormalizedDocumentSet** (fallback) — entities from document titles, findings from text
3. **RawSourceBundle / manifest** (fallback) — entities from `seed_entities`, placeholder findings

At least one of these must be provided.  Source attribution (source_index, citation_map)
is **merged** across all available artifacts so provenance is never lost.

### Quick Start

```bash
# Install core dependencies
pip install pydantic pydantic-settings click

# Recommended: generate from a fixture directory (Phase 2B/2A)
python -m content_research_pipeline.brief_cli generate \
    --fixture-dir demo_data/jwst_star_formation_early_universe_demo/ \
    --output-dir output/

# Generate from a KnowledgeGraphPackage (Phase 1.5 path)
python -m content_research_pipeline.brief_cli generate \
    --graph demo_data/jwst_star_formation_early_universe_demo/KnowledgeGraphPackage.sample.json \
    --output-dir output/

# Generate from the demo manifest (Phase 1 path, still supported)
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --output-dir output/

# Combine all upstream artifacts for richest output
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --documents demo_data/jwst_star_formation_early_universe_demo/NormalizedDocumentSet.sample.json \
    --graph demo_data/jwst_star_formation_early_universe_demo/KnowledgeGraphPackage.sample.json \
    --output-dir output/

# Validate the generated artifacts
python -m content_research_pipeline.brief_cli validate \
    --brief output/*__ResearchBrief__*.json \
    --run-manifest output/*__RunManifest__*.json
```

### Input Priority

| Input artifact | Content derived | When used |
|----------------|----------------|-----------|
| `KnowledgeGraphPackage` | Entities from graph nodes, findings from edges + node descriptions | Always preferred when provided |
| `NormalizedDocumentSet` | Entities from document titles, findings from document text | Fallback when no KG |
| `ChunkSet` | Chunk-level provenance recorded in RunManifest | Available but not used for content synthesis |
| `RawSourceBundle` | Entities from `seed_entities` (extension), placeholder findings | Fallback when no KG or NDS |

Source attribution (`source_index`, `citation_map`) merges from all provided artifacts,
preferring the richest metadata per `source_id` (bundle > documents > graph).

### What it produces

| Artifact | Description |
|----------|-------------|
| `ResearchBrief` | Structured research output with executive summary, key findings, entities, timeline, source index, citation map, open questions, and recommended angles. |
| `RunManifest` | Tracking artifact recording inputs, outputs, metrics, and status for the research run. |

Output filenames follow the naming convention: `<topic_slug>__<artifact_type>__<timestamp>.json`

### Validation

```bash
# Validate any ResearchBrief JSON against the shared contract
python -m content_research_pipeline.brief_cli validate --brief path/to/ResearchBrief.json

# Validate a RunManifest
python -m content_research_pipeline.brief_cli validate --run-manifest path/to/RunManifest.json
```

### Running Tests

```bash
# Run all Phase 1 + 1.5 + 2A + 2B + 3 + 4 tests (275 tests: 239 prior + 22 Phase 4 + 14 Phase 4.1 fix)
PYTHONPATH=src pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_upstream_artifacts.py tests/test_fixture_integration.py tests/test_phase2b_handoff.py tests/test_phase3_integration.py tests/test_phase4_artifact_transport.py -v --no-cov

# Run Phase 4 artifact-transport tests only (includes nested layout resolution tests)
PYTHONPATH=src pytest tests/test_phase4_artifact_transport.py -v --no-cov

# Run Phase 3 integration tests only
PYTHONPATH=src pytest tests/test_phase3_integration.py -v --no-cov

# Run all working tests (Phase 1/1.5/2A/2B/3/4 + config + prompts)
PYTHONPATH=src pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_upstream_artifacts.py tests/test_fixture_integration.py tests/test_phase2b_handoff.py tests/test_phase3_integration.py tests/test_phase4_artifact_transport.py tests/test_config.py tests/test_prompts.py -v --no-cov

# Run all tests (requires full dependencies from requirements.txt)
pytest tests/
```

### Audit

See [AUDIT.md](AUDIT.md) for the full audit package covering entrypoints,
contract alignment, happy-path status, contract field analysis, and implementation plan.

## Artifacts This Repo Owns

| Artifact | Status |
|----------|--------|
| `ResearchBrief` | ✓ Implemented (Phase 1.5 + 2A/2B enrichment) |
| `RunManifest` (research runs) | ✓ Implemented (Phase 1.5 + 2A/2B provenance) |

## Artifacts This Repo Consumes

| Artifact | Owner | Status |
|----------|-------|--------|
| `RawSourceBundle` | material-ingestion-pipeline | ✓ Consumed (primary or fallback input) |
| `NormalizedDocumentSet` | material-ingestion-pipeline | ✓ Consumed (primary or fallback input) |
| `ChunkSet` | material-ingestion-pipeline | ✓ Consumed (chunk-level provenance in RunManifest) |
| `KnowledgeGraphPackage` | material-ingestion-pipeline | ✓ Consumed (preferred input) |

## Contract Field Notes

### `seed_entities` — Internal Extension

The `seed_entities` field on `RawSourceBundle` is **not** part of the formal
shared contract (`contracts/shared_artifacts.json`).  It is an internal
convenience used by this repo when no richer upstream artifact is available.
Upstream repos may provide it but should not treat it as a contract obligation.

### Optional-vs-Required Field Mismatches

| Field | Artifact | Contract says | Pydantic model | Notes |
|-------|----------|---------------|----------------|-------|
| `retrieved_at` | `RawSourceItem` | Required (`source_item_required_fields`) | `Optional[str]` | Demo manifest has `null`; real ingestion should populate |
| `checksum` | `RawSourceItem` | Required (`source_item_required_fields`) | `Optional[str]` | Demo manifest has `null`; real ingestion should populate |
| `embeddings_index` | `KnowledgeGraphPackage` | Required (`required_fields`) | `Optional[str]` | May be `null` when embeddings are not yet computed |
| `entities` sub-fields | `ResearchBrief` | Not defined in contract | `List[Dict[str, Any]]` | Loosely typed; downstream should not assume fixed sub-schema |

### ChunkSet — Provenance Only

The `ChunkSet` is loaded and its producer/run_id are recorded in
`RunManifest.inputs.upstream_provenance`, but chunk content is not
currently used for synthesis (no LLM/embedding step).  The individual
`chunk_id` values from `KnowledgeGraphPackage.SourceRef.chunk_id` provide
a cross-reference path that can be resolved in a future enrichment step.

## Project Structure

```
content-research-pipeline/
├── src/content_research_pipeline/
│   ├── brief_cli.py               # CLI: generate & validate
│   ├── cli.py                     # Legacy CLI (web search pipeline)
│   ├── data/
│   │   ├── artifacts.py           # Contract-aligned Pydantic models
│   │   └── models.py              # Legacy pipeline models
│   ├── core/
│   │   ├── brief_generator.py     # ResearchBrief generation from artifacts
│   │   ├── fixture_loader.py      # Upstream fixture discovery and loading (Phase 2A/2B/3)
│   │   ├── pipeline.py            # Legacy web search pipeline
│   │   └── analysis.py            # NLP analysis module
│   ├── utils/
│   │   ├── contract_validator.py  # Validation against shared contract
│   │   └── caching.py             # Cache utilities
│   ├── config/                    # Settings, logging, prompts
│   ├── services/                  # Search, scraper, LLM, vector store
│   ├── visualization/             # HTML reports, charts
│   └── api/                       # FastAPI endpoints
├── contracts/                     # Shared cross-repo artifact contracts
│   ├── shared_artifacts.json
│   ├── schemas.md
│   └── demo_manifest.md
├── integration_fixtures/          # Canonical upstream/downstream handoff packages (Phase 3)
│   └── jwst/
│       ├── upstream/              # Upstream package (from material-ingestion-pipeline)
│       │   ├── handoff_manifest.json
│       │   ├── KnowledgeGraphPackage.json
│       │   ├── NormalizedDocumentSet.json
│       │   ├── ChunkSet.json
│       │   └── RawSourceBundle.json
│       └── downstream/            # Downstream package (for media-generation-pipeline)
│           ├── handoff_manifest.json
│           ├── ResearchBrief.json
│           └── RunManifest.json
├── demo_data/                     # Canonical demo scaffold + upstream fixtures
│   └── jwst_star_formation_early_universe_demo/
│       ├── manifest.json                       # RawSourceBundle (upstream)
│       ├── NormalizedDocumentSet.sample.json    # NDS upstream fixture
│       ├── ChunkSet.sample.json                # ChunkSet upstream fixture [Phase 2B]
│       ├── KnowledgeGraphPackage.sample.json   # KG upstream fixture
│       ├── ResearchBrief.sample.json           # Canonical output (generated)
│       ├── RunManifest.sample.json             # Canonical output (generated)
│       └── sources/
├── tests/
│   ├── test_artifacts.py          # Artifact model tests
│   ├── test_brief_generator.py    # Brief generation tests (Phase 1)
│   ├── test_upstream_artifacts.py # Upstream artifact tests (Phase 1.5)
│   ├── test_fixture_integration.py # Fixture-based integration tests (Phase 2A)
│   ├── test_phase2b_handoff.py    # Upstream handoff integration tests (Phase 2B)
│   ├── test_phase3_integration.py # Upstream/downstream handoff round-trip tests (Phase 3)
│   ├── test_phase4_artifact_transport.py # Artifact transport & workflow tests (Phase 4)
│   ├── test_contract_validator.py # Validation tests
│   ├── test_demo_contract.py      # Demo fixture contract tests
│   └── ...                        # Legacy pipeline tests
└── README.md
```

## Assumptions About Upstream Artifacts

- When a `KnowledgeGraphPackage` is available, it is the preferred source for
  entities and key findings.  The graph's `source_refs` are used for attribution.
- When only a `NormalizedDocumentSet` is available, entities are derived from
  document titles and findings from document text.
- When only a `RawSourceBundle` (manifest) is available, `seed_entities` (an
  internal extension, not a contract field) provides entity labels and placeholder
  findings are generated.
- `ChunkSet` chunks are recorded for provenance but not used for content synthesis
  in the current phase.  Their `source_id` and `document_id` fields should
  cross-reference the `RawSourceBundle` and `NormalizedDocumentSet` respectively.
- Source attribution (`source_index`, `citation_map`) is **merged** across all
  available artifacts.  Bundle sources provide the richest per-source metadata;
  graph and document sources fill gaps.

---

## Legacy Features

The repository also includes a full web search pipeline (search → scrape → analyze → visualize)
that requires additional dependencies (OpenAI, Google Search API, spaCy, Chroma, Redis).

### Full Installation (Legacy Pipeline)

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp env.example .env  # Configure API keys
```

### Legacy CLI Commands

```bash
# Full web research pipeline
python -m content_research_pipeline.cli research "topic query"

# Quick search
python -m content_research_pipeline.cli search "query" --type web

# Start web API server
python -m content_research_pipeline.cli serve

# Validate environment
python -m content_research_pipeline.cli validate
```

**Research and enrichment layer** of a 3-part AI workflow stack.

This repository consumes structured upstream artifacts from the [material-ingestion-pipeline](https://github.com/siddhant61/material-ingestion-pipeline) and produces a contract-compliant **ResearchBrief** for downstream [media-generation-pipeline](https://github.com/siddhant61/media-generation-pipeline).

## Cross-Repo Architecture

```
material-ingestion-pipeline          content-research-pipeline          media-generation-pipeline
────────────────────────────         ─────────────────────────          ──────────────────────────
RawSourceBundle ──────────────┐
NormalizedDocumentSet ────────┤
ChunkSet ─────────────────────┼──▶  ResearchBrief ──────────────────▶  ScenePlan
KnowledgeGraphPackage ────────┘     RunManifest                        MediaPackage
```

### Shared Contracts

All three repos share a versioned artifact contract:
- **Contract definition**: `contracts/shared_artifacts.json` (v1.0.0)
- **Schema documentation**: `contracts/schemas.md`
- **Demo manifest**: `contracts/demo_manifest.md`

## Phase 2A — Upstream Fixture Consumption

Phase 2A adds a stable fixture-based integration path for consuming real
upstream artifacts from `material-ingestion-pipeline`.

### Fixture Directory Loading

The new `--fixture-dir` CLI option auto-discovers all upstream artifacts
in a directory using well-known filenames:

```bash
# Recommended: load all upstream artifacts from a fixture directory
python -m content_research_pipeline.brief_cli generate \
    --fixture-dir demo_data/jwst_star_formation_early_universe_demo/ \
    --output-dir output/
```

The loader looks for:
| Filename | Artifact |
|----------|----------|
| `KnowledgeGraphPackage.sample.json` or `KnowledgeGraphPackage.json` | KnowledgeGraphPackage |
| `NormalizedDocumentSet.sample.json` or `NormalizedDocumentSet.json` | NormalizedDocumentSet |
| `manifest.json` or `RawSourceBundle.json` | RawSourceBundle |

### Provenance Preservation

When upstream artifacts are consumed, the `RunManifest.inputs.upstream_provenance`
field captures:
- Producer pipeline name and run ID for each artifact
- Full `provenance` dict from `KnowledgeGraphPackage` (pipeline, stage, source_artifact)

### Citation Enrichment

Source attribution is merged across all available artifacts.  When both a
`KnowledgeGraphPackage` and `RawSourceBundle` are provided:
- Source entries from the bundle provide rich metadata (org, URL, license)
- KG-only source entries are supplemented with bundle data where source_ids match

### Field Degradations (KG-Only Path)

When a `KnowledgeGraphPackage` is consumed without a `RawSourceBundle`:
| Field | Value | Reason |
|-------|-------|--------|
| `source_index[].origin_org` | `"unknown"` | KG source_refs lack org metadata |
| `source_index[].url` | `""` | KG source_refs lack URL metadata |
| `citation_map[].origin_org` | `"unknown"` | Same as above |
| `citation_map[].url` | `""` | Same as above |
| `citation_map[].license` | `"unknown"` | Same as above |

These degradations are fully resolved when a `RawSourceBundle` is also provided.

## Phase 1.5 — Upstream Artifact Consumption

The generator accepts any combination of upstream ingestion artifacts and applies
a priority-based fallback chain for content synthesis:

1. **KnowledgeGraphPackage** (preferred) — entities from nodes, findings from edges
2. **NormalizedDocumentSet** (fallback) — entities from document titles, findings from text
3. **RawSourceBundle / manifest** (fallback) — entities from `seed_entities`, placeholder findings

At least one of these must be provided.  Source attribution (source_index, citation_map)
is **merged** across all available artifacts so provenance is never lost.

### Quick Start

```bash
# Install core dependencies
pip install pydantic pydantic-settings click

# Recommended: generate from a fixture directory (Phase 2A)
python -m content_research_pipeline.brief_cli generate \
    --fixture-dir demo_data/jwst_star_formation_early_universe_demo/ \
    --output-dir output/

# Generate from a KnowledgeGraphPackage (Phase 1.5 path)
python -m content_research_pipeline.brief_cli generate \
    --graph demo_data/jwst_star_formation_early_universe_demo/KnowledgeGraphPackage.sample.json \
    --output-dir output/

# Generate from the demo manifest (Phase 1 path, still supported)
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --output-dir output/

# Combine all upstream artifacts for richest output
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --documents demo_data/jwst_star_formation_early_universe_demo/NormalizedDocumentSet.sample.json \
    --graph demo_data/jwst_star_formation_early_universe_demo/KnowledgeGraphPackage.sample.json \
    --output-dir output/

# Validate the generated artifacts
python -m content_research_pipeline.brief_cli validate \
    --brief output/*__ResearchBrief__*.json \
    --run-manifest output/*__RunManifest__*.json
```

### Input Priority

| Input artifact | Content derived | When used |
|----------------|----------------|-----------|
| `KnowledgeGraphPackage` | Entities from graph nodes, findings from edges + node descriptions | Always preferred when provided |
| `NormalizedDocumentSet` | Entities from document titles, findings from document text | Fallback when no KG |
| `RawSourceBundle` | Entities from `seed_entities` (extension), placeholder findings | Fallback when no KG or NDS |

Source attribution (`source_index`, `citation_map`) merges from all provided artifacts,
preferring the richest metadata per `source_id` (bundle > documents > graph).

### What it produces

| Artifact | Description |
|----------|-------------|
| `ResearchBrief` | Structured research output with executive summary, key findings, entities, timeline, source index, citation map, open questions, and recommended angles. |
| `RunManifest` | Tracking artifact recording inputs, outputs, metrics, and status for the research run. |

Output filenames follow the naming convention: `<topic_slug>__<artifact_type>__<timestamp>.json`

### Validation

```bash
# Validate any ResearchBrief JSON against the shared contract
python -m content_research_pipeline.brief_cli validate --brief path/to/ResearchBrief.json

# Validate a RunManifest
python -m content_research_pipeline.brief_cli validate --run-manifest path/to/RunManifest.json
```

### Running Tests

```bash
# Run all Phase 1 + 1.5 + 2A tests (models, generator, validator, demo, upstream, fixture integration)
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_upstream_artifacts.py tests/test_fixture_integration.py -v

# Run all working tests (Phase 1/1.5/2A + config + prompts)
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_upstream_artifacts.py tests/test_fixture_integration.py tests/test_config.py tests/test_prompts.py -v

# Run all tests (requires full dependencies from requirements.txt)
pytest tests/
```

### Audit

See [AUDIT.md](AUDIT.md) for the full audit package covering entrypoints,
contract alignment, happy-path status, contract field analysis, and implementation plan.

## Artifacts This Repo Owns

| Artifact | Status |
|----------|--------|
| `ResearchBrief` | ✓ Implemented (Phase 1.5 + 2A enrichment) |
| `RunManifest` (research runs) | ✓ Implemented (Phase 1.5 + 2A provenance) |

## Artifacts This Repo Consumes

| Artifact | Owner | Status |
|----------|-------|--------|
| `RawSourceBundle` | material-ingestion-pipeline | ✓ Consumed (primary or fallback input) |
| `NormalizedDocumentSet` | material-ingestion-pipeline | ✓ Consumed (primary or fallback input) |
| `ChunkSet` | material-ingestion-pipeline | ✓ Accepted (not yet used for synthesis) |
| `KnowledgeGraphPackage` | material-ingestion-pipeline | ✓ Consumed (preferred input) |

## Contract Field Notes

### `seed_entities` — Internal Extension

The `seed_entities` field on `RawSourceBundle` is **not** part of the formal
shared contract (`contracts/shared_artifacts.json`).  It is an internal
convenience used by this repo when no richer upstream artifact is available.
Upstream repos may provide it but should not treat it as a contract obligation.

### Optional-vs-Required Field Mismatches

| Field | Artifact | Contract says | Pydantic model | Notes |
|-------|----------|---------------|----------------|-------|
| `retrieved_at` | `RawSourceItem` | Required (`source_item_required_fields`) | `Optional[str]` | Demo manifest has `null`; real ingestion should populate |
| `checksum` | `RawSourceItem` | Required (`source_item_required_fields`) | `Optional[str]` | Demo manifest has `null`; real ingestion should populate |
| `embeddings_index` | `KnowledgeGraphPackage` | Required (`required_fields`) | `Optional[str]` | May be `null` when embeddings are not yet computed |
| `entities` sub-fields | `ResearchBrief` | Not defined in contract | `List[Dict[str, Any]]` | Loosely typed; downstream should not assume fixed sub-schema |

## Project Structure

```
content-research-pipeline/
├── src/content_research_pipeline/
│   ├── brief_cli.py               # CLI: generate & validate
│   ├── cli.py                     # Legacy CLI (web search pipeline)
│   ├── data/
│   │   ├── artifacts.py           # Contract-aligned Pydantic models
│   │   └── models.py              # Legacy pipeline models
│   ├── core/
│   │   ├── brief_generator.py     # ResearchBrief generation from artifacts
│   │   ├── fixture_loader.py      # Upstream fixture discovery and loading (Phase 2A)
│   │   ├── pipeline.py            # Legacy web search pipeline
│   │   └── analysis.py            # NLP analysis module
│   ├── utils/
│   │   ├── contract_validator.py  # Validation against shared contract
│   │   └── caching.py             # Cache utilities
│   ├── config/                    # Settings, logging, prompts
│   ├── services/                  # Search, scraper, LLM, vector store
│   ├── visualization/             # HTML reports, charts
│   └── api/                       # FastAPI endpoints
├── contracts/                     # Shared cross-repo artifact contracts
│   ├── shared_artifacts.json
│   ├── schemas.md
│   └── demo_manifest.md
├── demo_data/                     # Canonical demo scaffold + upstream fixtures
│   └── jwst_star_formation_early_universe_demo/
│       ├── manifest.json                       # RawSourceBundle
│       ├── NormalizedDocumentSet.sample.json    # NDS upstream fixture
│       ├── KnowledgeGraphPackage.sample.json   # KG upstream fixture
│       ├── ResearchBrief.sample.json           # Expected output sample
│       ├── RunManifest.sample.json             # Expected output sample
│       └── sources/
├── tests/
│   ├── test_artifacts.py          # Artifact model tests
│   ├── test_brief_generator.py    # Brief generation tests (Phase 1)
│   ├── test_upstream_artifacts.py # Upstream artifact tests (Phase 1.5)
│   ├── test_fixture_integration.py # Fixture-based integration tests (Phase 2A)
│   ├── test_contract_validator.py # Validation tests
│   ├── test_demo_contract.py      # Demo fixture contract tests
│   └── ...                        # Legacy pipeline tests
└── README.md
```

## Assumptions About Upstream Artifacts

- When a `KnowledgeGraphPackage` is available, it is the preferred source for
  entities and key findings.  The graph's `source_refs` are used for attribution.
- When only a `NormalizedDocumentSet` is available, entities are derived from
  document titles and findings from document text.
- When only a `RawSourceBundle` (manifest) is available, `seed_entities` (an
  internal extension, not a contract field) provides entity labels and placeholder
  findings are generated.
- Source attribution (`source_index`, `citation_map`) is **merged** across all
  available artifacts.  Bundle sources provide the richest per-source metadata;
  graph and document sources fill gaps.

---

## Legacy Features

The repository also includes a full web search pipeline (search → scrape → analyze → visualize)
that requires additional dependencies (OpenAI, Google Search API, spaCy, Chroma, Redis).

### Full Installation (Legacy Pipeline)

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp env.example .env  # Configure API keys
```

### Legacy CLI Commands

```bash
# Full web research pipeline
python -m content_research_pipeline.cli research "topic query"

# Quick search
python -m content_research_pipeline.cli search "query" --type web

# Start web API server
python -m content_research_pipeline.cli serve

# Validate environment
python -m content_research_pipeline.cli validate
``` 