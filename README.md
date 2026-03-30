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

## Phase 1 — Happy Path

The Phase 1 happy path reads the canonical demo manifest (a `RawSourceBundle`) and
produces a valid `ResearchBrief` JSON plus a `RunManifest` tracking artifact.

### Quick Start

```bash
# Install core dependencies (pydantic, click)
pip install pydantic pydantic-settings click

# Generate a ResearchBrief from the demo manifest
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --output-dir output/

# Validate the generated artifacts
python -m content_research_pipeline.brief_cli validate \
    --brief output/jwst_star_formation_early_universe_demo__ResearchBrief__*.json \
    --run-manifest output/jwst_star_formation_early_universe_demo__RunManifest__*.json
```

### What it produces

| Artifact | Description |
|----------|-------------|
| `ResearchBrief` | Structured research output with executive summary, key findings, entities, timeline, source index, citation map, open questions, and recommended angles. |
| `RunManifest` | Tracking artifact recording inputs, outputs, metrics, and status for the research run. |

Output filenames follow the naming convention: `<topic_slug>__<artifact_type>__<timestamp>.json`

### Consuming upstream artifacts

The generator supports optional upstream artifacts for richer output:

```bash
python -m content_research_pipeline.brief_cli generate \
    --manifest path/to/RawSourceBundle.json \
    --documents path/to/NormalizedDocumentSet.json \
    --chunks path/to/ChunkSet.json \
    --graph path/to/KnowledgeGraphPackage.json \
    --output-dir output/
```

When a `KnowledgeGraphPackage` is provided, entities are derived from graph nodes.
When a `NormalizedDocumentSet` is provided, key findings are extracted from documents.

### Validation

```bash
# Validate any ResearchBrief JSON against the shared contract
python -m content_research_pipeline.brief_cli validate --brief path/to/ResearchBrief.json

# Validate a RunManifest
python -m content_research_pipeline.brief_cli validate --run-manifest path/to/RunManifest.json
```

### Running Tests

```bash
# Run Phase 1 tests (models, generator, validator, demo contract)
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py -v

# Run all working tests (Phase 1 + config + prompts)
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py tests/test_demo_contract.py tests/test_config.py tests/test_prompts.py -v

# Run all tests (requires full dependencies from requirements.txt)
pytest tests/
```

### Audit

See [AUDIT.md](AUDIT.md) for the full Phase 1 audit package covering entrypoints,
contract alignment, happy-path status, broken paths, and implementation plan.

## Artifacts This Repo Owns

| Artifact | Status |
|----------|--------|
| `ResearchBrief` | ✓ Implemented (Phase 1) |
| `RunManifest` (research runs) | ✓ Implemented (Phase 1) |

## Artifacts This Repo Consumes

| Artifact | Owner | Status |
|----------|-------|--------|
| `RawSourceBundle` | material-ingestion-pipeline | ✓ Consumed (manifest-driven) |
| `NormalizedDocumentSet` | material-ingestion-pipeline | ✓ Supported (optional input) |
| `ChunkSet` | material-ingestion-pipeline | ✓ Supported (optional input) |
| `KnowledgeGraphPackage` | material-ingestion-pipeline | ✓ Supported (optional input) |

## Project Structure

```
content-research-pipeline/
├── src/content_research_pipeline/
│   ├── brief_cli.py               # Phase 1 CLI: generate & validate
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
├── demo_data/                     # Canonical demo scaffold
│   └── jwst_star_formation_early_universe_demo/
│       ├── manifest.json          # RawSourceBundle for JWST demo
│       ├── ResearchBrief.sample.json
│       ├── RunManifest.sample.json
│       └── sources/
├── tests/
│   ├── test_artifacts.py          # Artifact model tests
│   ├── test_brief_generator.py    # Brief generation tests
│   ├── test_contract_validator.py # Validation tests
│   └── ...                        # Legacy pipeline tests
└── README.md
```

## Assumptions About Upstream Artifacts

- The `RawSourceBundle` (demo manifest) is treated as the primary input in Phase 1.
- When upstream `NormalizedDocumentSet`, `ChunkSet`, or `KnowledgeGraphPackage` artifacts
  are not yet available, the generator produces a valid brief from manifest metadata and
  seed entities alone.
- Source attribution is preserved from the manifest's `sources[]` into the brief's
  `source_index[]` and `citation_map`.

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