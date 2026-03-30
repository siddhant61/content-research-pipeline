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

# Generate from a KnowledgeGraphPackage (preferred path)
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
# Run all Phase 1 + 1.5 tests (models, generator, validator, demo contract, upstream artifacts)
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_upstream_artifacts.py -v

# Run all working tests (Phase 1/1.5 + config + prompts)
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_upstream_artifacts.py tests/test_config.py tests/test_prompts.py -v

# Run all tests (requires full dependencies from requirements.txt)
pytest tests/
```

### Audit

See [AUDIT.md](AUDIT.md) for the full audit package covering entrypoints,
contract alignment, happy-path status, contract field analysis, and implementation plan.

## Artifacts This Repo Owns

| Artifact | Status |
|----------|--------|
| `ResearchBrief` | ✓ Implemented (Phase 1.5) |
| `RunManifest` (research runs) | ✓ Implemented (Phase 1.5) |

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