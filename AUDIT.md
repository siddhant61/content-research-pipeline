# Audit Package — content-research-pipeline

**Date:** 2026-03-30
**Schema version:** 1.0.0
**Auditor:** Phase 1 audit pass

---

## 1. Current Entrypoints

| Entrypoint | Module | Type | Status |
|------------|--------|------|--------|
| `content-research-brief generate` | `brief_cli.py` | Click CLI | ✅ Working — Phase 1 happy path |
| `content-research-brief validate` | `brief_cli.py` | Click CLI | ✅ Working — contract validation |
| `content-research research` | `cli.py` | Click CLI | ⚠️ Requires full legacy deps (OpenAI, Google, spaCy, Chroma, Redis) |
| `content-research search` | `cli.py` | Click CLI | ⚠️ Requires Google API |
| `content-research serve` | `cli.py` | Click CLI / FastAPI | ⚠️ Requires FastAPI + all legacy deps |
| `content-research cache` | `cli.py` | Click CLI | ⚠️ Requires Redis |
| `content-research config` | `cli.py` | Click CLI | ⚠️ Requires settings load with API keys |
| `content-research validate` | `cli.py` | Click CLI | ⚠️ Requires spaCy, API keys |
| `python -m content_research_pipeline.brief_cli` | `brief_cli.py` | Module | ✅ Working |
| `python -m content_research_pipeline.cli` | `cli.py` | Module | ⚠️ Requires full deps |
| FastAPI `/research` endpoint | `api/main.py` | HTTP API | ⚠️ Requires FastAPI + all deps |

**Summary:** Only `brief_cli.py` (generate, validate) works with minimal dependencies. All legacy entrypoints require the full 66-package `requirements.txt`, which includes pinned versions of heavy deps (langchain 0.1.0, openai 1.3.0, chromadb 0.4.20, spacy 3.7.2, numpy 1.24.3, etc.).

---

## 2. Repo Purpose as Implemented Today

The repository serves **two distinct roles**:

### Role A: Phase 1 Research Brief Generator (new, working)
- Reads a `RawSourceBundle` manifest (JSON) and optionally `NormalizedDocumentSet`, `ChunkSet`, `KnowledgeGraphPackage`
- Produces a contract-compliant `ResearchBrief` + `RunManifest`
- Validates output against `contracts/shared_artifacts.json`
- No LLM, no external API calls, no heavy dependencies
- Implemented in: `brief_cli.py`, `core/brief_generator.py`, `data/artifacts.py`, `utils/contract_validator.py`

### Role B: Legacy Web Search Pipeline (pre-existing, broken without full deps)
- Multi-source web search → scrape → analyze → visualize → HTML report
- Requires OpenAI, Google Search, spaCy, Chroma, Redis
- Produces `PipelineResult` (internal model, NOT contract-aligned)
- Implemented in: `cli.py`, `core/pipeline.py`, `core/analysis.py`, `services/*`, `visualization/*`, `api/*`

**Role A is the future.** Role B is a pre-existing codebase that predates the 3-repo architecture.

---

## 3. Mismatch vs README

The current README (updated in the previous Phase 1 PR) is **mostly accurate** for the Phase 1 path. Remaining mismatches:

| README Claim | Reality | Severity |
|-------------|---------|----------|
| "Quick Start" says `pip install pydantic pydantic-settings click` | Works, but `loguru` is also needed (imported by settings.py via logging.py) | Low — minor docs gap |
| "Run all tests" says `pytest tests/` | 8 of 15 test files fail to import due to missing heavy deps (langchain, fastapi, redis, etc.) | Medium — misleading |
| README says `test_pipeline.py` is a "Legacy pipeline test" | It tests `ContentResearchPipeline` which requires full deps to import | Low — label is correct |
| Project Structure section omits some files | Missing: `services/job_store.py`, `visualization/__init__.py`, various legacy docs | Low — cosmetic |
| No mention of `validation_check.py` (root-level) | Exists but references legacy structure only | Low — orphaned file |

**No critical README mismatches.** The Phase 1 happy path documentation is accurate and runnable.

---

## 4. Mismatch vs contracts/shared_artifacts.json and contracts/schemas.md

### ResearchBrief: ✅ Fully Aligned

| Contract Requirement | Model (artifacts.py) | Generated Output | Status |
|---------------------|---------------------|-----------------|--------|
| 16 required fields | All 16 present in Pydantic model | All 16 emitted in JSON | ✅ |
| `key_findings[]` sub-fields (5) | `KeyFinding` model has all 5 | All 5 present | ✅ |
| `source_index[]` sub-fields (6) | `SourceIndexEntry` model has all 6 | All 6 present | ✅ |
| `entities` | `List[Dict[str, Any]]` (flexible) | Populated from seeds/graph | ✅ |
| `citation_map` | `Dict[str, Any]` | Populated from bundle | ✅ |

### RunManifest: ✅ Fully Aligned

| Contract Requirement | Model (artifacts.py) | Generated Output | Status |
|---------------------|---------------------|-----------------|--------|
| 13 required fields | All 13 present | All 13 emitted | ✅ |

### Consumed Artifacts: ✅ Models Present

| Artifact | Pydantic Model | Loader Function | Contract Fields Covered |
|----------|---------------|-----------------|------------------------|
| `RawSourceBundle` | ✅ `RawSourceBundle` + `RawSourceItem` | ✅ `load_raw_source_bundle()` | All required fields |
| `NormalizedDocumentSet` | ✅ `NormalizedDocumentSet` + `NormalizedDocument` + `DocumentSection` | ✅ `load_normalized_document_set()` | All required fields |
| `ChunkSet` | ✅ `ChunkSet` + `Chunk` | ✅ `load_chunk_set()` | All required fields |
| `KnowledgeGraphPackage` | ✅ `KnowledgeGraphPackage` + `GraphNode` + `GraphEdge` + `SourceRef` | ✅ `load_knowledge_graph()` | All required fields |

### Minor Gaps

| Gap | Detail | Impact |
|-----|--------|--------|
| `RawSourceItem.retrieved_at` is `Optional` | Contract lists it as required in `source_item_required_fields` but the demo manifest has `null` values. The Pydantic model tolerates `None`. | Low — demo scaffold uses null; real ingestion output should populate this |
| `RawSourceItem.checksum` is `Optional` | Same as above — required per contract but null in demo manifest | Low — same justification |
| `entities` field is `List[Dict[str, Any]]` | Untyped dict rather than a dedicated Pydantic model. The contract's schemas.md doesn't define entity sub-fields, so a loose type is acceptable. | Low — could be tightened later |
| Contract validator only validates top-level required fields | Does not check sub-item required fields (e.g., `source_item_required_fields`, `chunk_required_fields`) | Medium — sub-item validation would catch malformed upstream artifacts |
| Filename convention | Implementation uses `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")` — matches contract pattern `<topic_slug>__<artifact_type>__<timestamp>.json` | ✅ Correct |

---

## 5. Happy-Path Status

### Phase 1 Happy Path: ✅ Working End-to-End

```
manifest.json (RawSourceBundle) → brief_cli generate → ResearchBrief.json + RunManifest.json
```

**Verified commands:**

```bash
# Generate
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --output-dir output/

# Validate
python -m content_research_pipeline.brief_cli validate \
    --brief output/jwst_star_formation_early_universe_demo__ResearchBrief__*.json \
    --run-manifest output/jwst_star_formation_early_universe_demo__RunManifest__*.json
```

**Output verified:**
- ResearchBrief: 16/16 required fields present, all sub-schemas correct
- RunManifest: 13/13 required fields present
- Source attribution preserved: 6 sources in `source_index` and `citation_map`
- 10 seed entities mapped into `entities`
- File naming convention matches contract

**Tests verified:**
- 35/35 Phase 1 tests pass (test_artifacts, test_brief_generator, test_contract_validator)
- Tests cover: model round-trips, generation from manifest, generation with graph/documents, source attribution, contract validation, file I/O

### Legacy Happy Path: ❌ Not runnable without full environment

The legacy pipeline (`cli.py research "topic"`) requires:
- `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_CSE_ID` environment variables
- Full `requirements.txt` installed (66 packages including numpy, spacy, langchain, chromadb)
- spaCy `en_core_web_sm` model downloaded
- Redis running (for caching)
- Produces `PipelineResult` — NOT a contract-aligned `ResearchBrief`

---

## 6. Broken or Fragile Paths

| Path | Problem | Severity |
|------|---------|----------|
| `pytest tests/` (full suite) | 8 test files fail to import: `test_analysis`, `test_api`, `test_caching`, `test_credibility`, `test_integration`, `test_job_store`, `test_pipeline`, `test_scraper` — all due to missing heavy deps (langchain_openai, fastapi, redis, google-api-python-client, etc.) | Medium — misleading CI unless selective test runs |
| `test_visualization.py` | 4 tests ERROR at setup (chart generator fixture fails), 1 FAILED (report with analysis uses old API) | Medium — partial breakage |
| Legacy CLI commands | All require full deps + env vars. No graceful fallback. | Low — expected for legacy |
| `data/models.py` | Uses Pydantic V1 `@validator` syntax, `class Config` — triggers deprecation warnings with Pydantic V2 | Low — warnings only, still functional |
| `config/settings.py` | Uses `Field(..., env="...")` (deprecated in Pydantic V2), Pydantic V1 `@validator` syntax | Low — warnings only |
| `validation_check.py` (root) | References legacy structure only, skips import checks, not connected to Phase 1 | Low — orphaned utility |
| CI workflow `ci.yml` | `--cov-fail-under=80` will fail if only Phase 1 tests run (Phase 1 covers fewer source lines than 80%) | Medium — CI may fail |
| Docker/compose files in `.gitignore` | `Dockerfile` and `docker-compose.yml` exist but are gitignored (`*.yml` pattern), meaning legacy deploy path is partially orphaned | Low — legacy concern |

---

## 7. Highest-Leverage Phase 1 Changes

Ranked by impact-to-effort ratio:

| Priority | Change | Why | Effort |
|----------|--------|-----|--------|
| **P0** | Add sub-item field validation to `contract_validator.py` | Currently only validates top-level required fields. Upstream artifact malformation (missing `source_id` in a source item, etc.) would pass silently. | Small |
| **P1** | Test isolation: mark legacy tests with `@pytest.mark.legacy` or skip without deps | `pytest tests/` currently fails with 8 collection errors. Phase 1 tests should run cleanly in CI. | Small |
| **P2** | Tighten `entities` field typing | Currently `List[Dict[str, Any]]` — could be a dedicated `BriefEntity` model to match the structured pattern of other sub-items. | Small |
| **P3** | Add a `--dry-run` or `--check` mode to `brief_cli generate` | Would validate the manifest parses correctly without writing files — useful for CI and debugging. | Small |
| **P4** | Align `RawSourceItem.retrieved_at` and `.checksum` optionality | Mark these as `Optional` explicitly with a note that real ingestion output should populate them. Already done, but add a doc comment. | Trivial |
| **P5** | Wire brief generation into the legacy `cli.py research` flow | When full deps are available, the legacy pipeline could emit a `ResearchBrief` instead of/alongside the `PipelineResult`. This is a bridge, not Phase 1. | Medium — defer to Phase 2 |
| **P6** | Deprecation warning cleanup in `models.py` and `settings.py` | Migrate from Pydantic V1 `@validator` to V2 `@field_validator`, from `class Config` to `ConfigDict`. | Medium — defer to Phase 2 |

---

## 8. Proposed Implementation Order

### Phase 1 (this audit + minimal scaffolding) — CURRENT

1. ✅ Audit complete (this document)
2. ✅ `data/artifacts.py` — contract-aligned Pydantic models
3. ✅ `core/brief_generator.py` — manifest-to-brief generation
4. ✅ `utils/contract_validator.py` — validation against shared_artifacts.json
5. ✅ `brief_cli.py` — standalone CLI
6. ✅ 35 tests passing
7. ✅ README updated for Phase 1

### Phase 1.1 (immediate follow-up, high leverage)

1. Add sub-item validation to `contract_validator.py` (P0)
2. Isolate legacy tests to prevent CI noise (P1)

### Phase 2 (next iteration)

1. Tighten entity typing (P2)
2. Add `--dry-run` mode (P3)
3. Bridge legacy pipeline to emit `ResearchBrief` alongside `PipelineResult` (P5)
4. Pydantic V2 migration for legacy modules (P6)
5. LLM-powered synthesis (richer `executive_summary`, `key_findings` from actual document text)

### Phase 3 (later)

1. Real upstream artifact consumption (actual `NormalizedDocumentSet` and `KnowledgeGraphPackage` from material-ingestion-pipeline)
2. Embedding-based semantic search over chunks for evidence retrieval
3. API endpoint for brief generation (`POST /brief`)

---

## 9. Validation Plan

### Current Validation (Phase 1)

| What | How | Status |
|------|-----|--------|
| Artifact models match contract | Automated: Pydantic model fields compared against `shared_artifacts.json` required_fields | ✅ Verified |
| Generated brief has all required fields | Automated: `validate_research_brief()` check in CLI | ✅ Verified |
| Generated manifest has all required fields | Automated: `validate_run_manifest()` check in CLI | ✅ Verified |
| Source attribution preserved | Test: `test_generate_preserves_source_attribution` | ✅ Passing |
| End-to-end demo manifest → brief | Test: `test_end_to_end_demo_manifest` | ✅ Passing |
| File naming convention | Test: `test_output_filenames_follow_convention` | ✅ Passing |
| Happy path CLI | Manual: `brief_cli generate --manifest ...` verified | ✅ Verified |

### Recommended Additions (Phase 1.1)

| What | How | Priority |
|------|-----|----------|
| Sub-item field validation | Extend `contract_validator.py` to check `source_item_required_fields`, `chunk_required_fields`, etc. | P0 |
| Legacy test isolation | Add `@pytest.mark.legacy` marker and skip condition; or use `importorskip` | P1 |
| CI green path | Ensure `pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py` is the default CI target for Phase 1 | P1 |
| Sample artifact validation | Add a test that validates `demo_data/*/*.sample.json` against the contract | P0 |

---

## 10. Cross-Repo Implications

### For material-ingestion-pipeline

| Implication | Detail |
|------------|--------|
| This repo consumes `RawSourceBundle` | The demo manifest (`manifest.json`) is the contract handoff point. Material-ingestion should produce manifests in this exact shape. |
| `retrieved_at` and `checksum` fields | The demo manifest has `null` values for these. Real ingestion output should populate them. The content-research-pipeline tolerates `null` but downstream consumers may not. |
| `seed_entities` field | Used by the brief generator for entity population. This is NOT in the formal `required_fields` for `RawSourceBundle` in the contract — it's an extension. Material-ingestion should continue providing it. |
| `status` and `notes` fields | Present in the demo manifest but not in the contract's `required_fields`. These are informational extensions. No action required. |
| Artifact naming | Both repos should use `<topic_slug>__<artifact_type>__<timestamp>.json`. Currently aligned. |

### For media-generation-pipeline

| Implication | Detail |
|------------|--------|
| This repo produces `ResearchBrief` | Media-generation should consume the exact shape emitted by `brief_cli generate`. Contract fields verified. |
| `entities` field shape | Currently `List[Dict[str, Any]]` — media-generation should not assume typed sub-fields beyond what the dict contains (entity_id, label, entity_type, source_refs). |
| `key_findings[].evidence_refs` | Currently empty in placeholder findings. Real findings will have source_id references. Media-generation should handle empty lists gracefully. |
| `timeline` | Currently empty list. Media-generation should handle empty timelines. |
| `citation_map` | Keyed by `source_id` → `{title, url, origin_org, license}`. Media-generation can use this for attribution overlays. |

### Contract Tensions

| Tension | Detail | Recommendation |
|---------|--------|----------------|
| `seed_entities` is not in the formal contract | Used by content-research but not defined in `shared_artifacts.json` | Add as an optional field in the next contract revision, or document as a convention |
| `entities` sub-schema undefined | The contract's `schemas.md` lists `entities` as a required field on `ResearchBrief` but doesn't define the sub-item schema | Define sub-fields in the next contract revision (entity_id, label, entity_type, source_refs) |
| No `enriched KnowledgeGraphPackage` contract | `schemas.md` says content-research-pipeline owns "optional enriched KnowledgeGraphPackage" but there's no enrichment schema defined | Defer — not needed for Phase 1 |

---

## Appendix: Test Results Summary

### Phase 1 Tests (47/47 passing)
```
tests/test_artifacts.py           — 8 passed
tests/test_brief_generator.py     — 12 passed
tests/test_contract_validator.py  — 15 passed
tests/test_demo_contract.py       — 12 passed
```

### Phase 1.5 Tests (44/44 passing)
```
tests/test_upstream_artifacts.py  — 44 passed
  TestKGDrivenBrief               — 10 tests (KG-only brief, entities, findings, attribution, contract)
  TestNDSDrivenBrief              — 7 tests (NDS-only brief, entities, findings, attribution, contract)
  TestFallbackBehavior            — 9 tests (priority chain, topic resolution, source merging)
  TestContractOutput              — 6 tests (all input combos produce valid output)
  TestGenerateBriefFromArtifacts  — 7 tests (convenience function, file I/O, contract)
  TestDemoFixtureContract         — 5 tests (demo KG/NDS fixture validation)
```

### Working Legacy Tests (18/18 passing)
```
tests/test_config.py          — 5 passed
tests/test_prompts.py         — 13 passed
```

### Broken Legacy Tests (8 files, collection errors)
```
tests/test_analysis.py       — ModuleNotFoundError: langchain_openai
tests/test_api.py             — ModuleNotFoundError: fastapi
tests/test_caching.py         — ModuleNotFoundError: redis
tests/test_credibility.py     — ModuleNotFoundError: langchain_openai
tests/test_integration.py     — ModuleNotFoundError: fastapi
tests/test_job_store.py       — ModuleNotFoundError: redis
tests/test_pipeline.py        — ModuleNotFoundError: googleapiclient
tests/test_scraper.py         — ModuleNotFoundError: trafilatura
```

### Partial Legacy Tests (test_visualization.py)
```
4 tests ERROR at setup (chart generator fixture)
1 test FAILED (report with analysis)
3 tests PASSED
```

---

## Phase 1.5 Worklog

**Date:** 2026-03-30
**Scope:** Upstream artifact consumption — KG/NDS-driven ResearchBrief generation

### What changed

| Component | Change | Why |
|-----------|--------|-----|
| `core/brief_generator.py` | `BriefGenerator.bundle` is now `Optional`; added `_resolve_topic()`, `_resolve_source_index()`, `_resolve_citation_map()`, `_resolve_entities()`, `_resolve_findings()` methods | Enables KG-only and NDS-only brief generation |
| `core/brief_generator.py` | New functions: `_build_source_index_from_graph()`, `_build_source_index_from_documents()`, `_build_citation_map_from_graph()`, `_build_citation_map_from_documents()`, `_build_entities_from_documents()`, `_build_findings_from_graph()` | Source attribution and content extraction from non-bundle artifacts |
| `core/brief_generator.py` | New `generate_brief_from_artifacts()` convenience function | Flexible entry point that accepts any combination of upstream artifacts |
| `brief_cli.py` | `--manifest` is no longer required; CLI requires at least one of `--manifest`, `--documents`, `--graph` | Enables KG-first or NDS-first workflows |
| `brief_cli.py` | Version bumped to 1.5.0 | Reflects new capability |
| Demo fixtures | Added `KnowledgeGraphPackage.sample.json` and `NormalizedDocumentSet.sample.json` | Canonical upstream artifact samples for testing |
| Tests | Added `tests/test_upstream_artifacts.py` (44 tests) | KG-driven, NDS-driven, fallback, and contract validation coverage |
| `README.md` | Updated for Phase 1.5: input priority table, new quick start examples, contract field notes, seed_entities documented as extension | Documentation accuracy |
| `AUDIT.md` | Added Phase 1.5 worklog section | Audit trail |

### Input priority (defined and tested)

1. **KnowledgeGraphPackage** — entities from `nodes`, findings from `edges` + node descriptions
2. **NormalizedDocumentSet** — entities from document titles, findings from document `text`
3. **RawSourceBundle** — entities from `seed_entities` (internal extension), placeholder findings

Source attribution merges across all available artifacts: `bundle > documents > graph`.

### `seed_entities` — documented as internal extension

The `seed_entities` field on `RawSourceBundle` is **not** defined in `contracts/shared_artifacts.json`
`required_fields`.  It is used only as a fallback when no richer upstream artifact is available.
It is now explicitly documented in `_build_entities_from_seeds()` and in `README.md`.

### Optional-vs-required field mismatches (documented)

| Field | Artifact | Contract says | Model says | Impact |
|-------|----------|---------------|------------|--------|
| `retrieved_at` | `RawSourceItem` | Required in `source_item_required_fields` | `Optional[str]` | Demo uses `null`; real ingestion should populate |
| `checksum` | `RawSourceItem` | Required in `source_item_required_fields` | `Optional[str]` | Demo uses `null`; real ingestion should populate |
| `embeddings_index` | `KnowledgeGraphPackage` | Required in `required_fields` | `Optional[str]` | May be `null` before embedding computation |
| `entities` sub-fields | `ResearchBrief` | Not defined in contract | `List[Dict[str, Any]]` | Loosely typed; downstream should not assume sub-schema |
| `seed_entities` | `RawSourceBundle` | Not in `required_fields` | `Optional[List[str]]` | Internal extension, not a contract obligation |
| `status`, `notes` | `RawSourceBundle` | Not in `required_fields` | `Optional` | Informational extensions in demo scaffold |

### Validated commands

```bash
# KG-only generation
python -m content_research_pipeline.brief_cli generate \
    --graph demo_data/jwst_star_formation_early_universe_demo/KnowledgeGraphPackage.sample.json \
    --output-dir output/

# NDS-only generation
python -m content_research_pipeline.brief_cli generate \
    --documents demo_data/jwst_star_formation_early_universe_demo/NormalizedDocumentSet.sample.json \
    --output-dir output/

# Manifest-only (Phase 1 path, still supported)
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --output-dir output/

# All artifacts combined
python -m content_research_pipeline.brief_cli generate \
    --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \
    --documents demo_data/jwst_star_formation_early_universe_demo/NormalizedDocumentSet.sample.json \
    --graph demo_data/jwst_star_formation_early_universe_demo/KnowledgeGraphPackage.sample.json \
    --output-dir output/

# Tests
pytest tests/test_artifacts.py tests/test_brief_generator.py tests/test_contract_validator.py \
    tests/test_demo_contract.py tests/test_upstream_artifacts.py -v --no-cov
```

### Cross-repo implications

| For | Implication |
|-----|-------------|
| material-ingestion-pipeline | This repo now actively consumes `KnowledgeGraphPackage` and `NormalizedDocumentSet`. Ingestion should produce these in the contract-defined shape. |
| media-generation-pipeline | No changes to `ResearchBrief` shape. Output remains contract-compliant regardless of input source. |
| Contract | `seed_entities` is used but not required. No contract changes needed. |

### What remains

- ChunkSet is accepted but not yet used for synthesis (could enable chunk-level evidence retrieval)
- LLM-powered synthesis for richer `executive_summary` and `key_findings`
- API endpoint for brief generation (`POST /brief`)
- Legacy pipeline bridge to emit `ResearchBrief` alongside `PipelineResult`
