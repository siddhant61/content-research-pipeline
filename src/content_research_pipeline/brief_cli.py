"""
Standalone CLI for the Content Research Pipeline.

Generate a ResearchBrief from upstream artifacts (KnowledgeGraphPackage,
NormalizedDocumentSet, and/or RawSourceBundle manifest).

Usage:
    # From manifest (Phase 1 path)
    python -m content_research_pipeline.brief_cli generate \\
        --manifest demo_data/jwst_star_formation_early_universe_demo/manifest.json \\
        --output-dir output/

    # From a KnowledgeGraphPackage (Phase 1.5 — preferred)
    python -m content_research_pipeline.brief_cli generate \\
        --graph path/to/KnowledgeGraphPackage.json \\
        --output-dir output/

    # Validate
    python -m content_research_pipeline.brief_cli validate \\
        --brief output/jwst_star_formation_early_universe_demo__ResearchBrief__*.json
"""

import json
import sys
from pathlib import Path

import click

from .core.brief_generator import (
    BriefGenerator,
    generate_brief_from_artifacts,
    generate_brief_from_manifest,
    load_raw_source_bundle,
)
from .utils.contract_validator import (
    validate_brief_file,
    validate_manifest_file,
    validate_research_brief,
    validate_run_manifest,
)


@click.group()
@click.version_option(version="1.5.0")
def brief_cli():
    """Content Research Pipeline — brief generation and validation."""
    pass


@brief_cli.command()
@click.option(
    "--manifest", "-m",
    default=None,
    type=click.Path(exists=True),
    help="Path to a RawSourceBundle JSON (e.g. demo manifest.json).",
)
@click.option(
    "--question", "-q",
    default=None,
    help="Override the default research question.",
)
@click.option(
    "--documents",
    default=None,
    type=click.Path(exists=True),
    help="Optional path to a NormalizedDocumentSet JSON.",
)
@click.option(
    "--chunks",
    default=None,
    type=click.Path(exists=True),
    help="Optional path to a ChunkSet JSON.",
)
@click.option(
    "--graph",
    default=None,
    type=click.Path(exists=True),
    help="Optional path to a KnowledgeGraphPackage JSON.",
)
@click.option(
    "--output-dir", "-o",
    default="output",
    type=click.Path(),
    help="Directory to write output files (default: output/).",
)
def generate(manifest, question, documents, chunks, graph, output_dir):
    """Generate a ResearchBrief from upstream artifacts.

    At least one of --manifest, --documents, or --graph must be provided.

    Input priority:
      1. KnowledgeGraphPackage (--graph)  — richest structured input
      2. NormalizedDocumentSet (--documents) — document-level content
      3. RawSourceBundle (--manifest) — source metadata / seed entities
    """
    if not manifest and not documents and not graph:
        click.echo(
            "Error: at least one of --manifest, --documents, or --graph "
            "must be provided.",
            err=True,
        )
        sys.exit(1)

    inputs = []
    if manifest:
        inputs.append(f"manifest: {manifest}")
    if documents:
        inputs.append(f"documents: {documents}")
    if graph:
        inputs.append(f"graph: {graph}")
    click.echo(f"Loading inputs: {', '.join(inputs)}")

    result = generate_brief_from_artifacts(
        manifest_path=manifest,
        research_question=question,
        documents_path=documents,
        chunks_path=chunks,
        graph_path=graph,
        output_dir=output_dir,
    )

    click.echo(f"\n✓ ResearchBrief written to: {result['brief_path']}")
    click.echo(f"✓ RunManifest written to:   {result['manifest_path']}")

    # Quick validation
    brief_data = result["brief"].model_dump()
    is_valid, errors = validate_research_brief(brief_data)
    if is_valid:
        click.echo("\n✓ ResearchBrief passes contract validation.")
    else:
        click.echo("\n✗ Validation errors:")
        for err in errors:
            click.echo(f"  - {err}")
        sys.exit(1)

    manifest_data = result["run_manifest"].model_dump()
    is_valid, errors = validate_run_manifest(manifest_data)
    if is_valid:
        click.echo("✓ RunManifest passes contract validation.")
    else:
        click.echo("✗ RunManifest validation errors:")
        for err in errors:
            click.echo(f"  - {err}")
        sys.exit(1)

    # Summary
    brief = result["brief"]
    click.echo(f"\nTopic:       {brief.topic}")
    click.echo(f"Question:    {brief.research_question}")
    click.echo(f"Sources:     {len(brief.source_index)}")
    click.echo(f"Entities:    {len(brief.entities)}")
    click.echo(f"Findings:    {len(brief.key_findings)}")
    click.echo(f"Citations:   {len(brief.citation_map)}")


@brief_cli.command("validate")
@click.option(
    "--brief", "-b",
    default=None,
    type=click.Path(exists=True),
    help="Path to a ResearchBrief JSON to validate.",
)
@click.option(
    "--run-manifest", "-r",
    default=None,
    type=click.Path(exists=True),
    help="Path to a RunManifest JSON to validate.",
)
@click.option(
    "--contract",
    default=None,
    type=click.Path(exists=True),
    help="Path to the shared_artifacts.json contract (auto-detected by default).",
)
def validate(brief, run_manifest, contract):
    """Validate artifact JSON files against the shared contract."""
    if not brief and not run_manifest:
        click.echo("Provide at least --brief or --run-manifest to validate.")
        sys.exit(1)

    all_valid = True

    if brief:
        click.echo(f"Validating ResearchBrief: {brief}")
        is_valid, errors = validate_brief_file(brief, contract)
        if is_valid:
            click.echo("  ✓ Valid ResearchBrief.")
        else:
            click.echo("  ✗ Validation errors:")
            for err in errors:
                click.echo(f"    - {err}")
            all_valid = False

    if run_manifest:
        click.echo(f"Validating RunManifest: {run_manifest}")
        is_valid, errors = validate_manifest_file(run_manifest, contract)
        if is_valid:
            click.echo("  ✓ Valid RunManifest.")
        else:
            click.echo("  ✗ Validation errors:")
            for err in errors:
                click.echo(f"    - {err}")
            all_valid = False

    if all_valid:
        click.echo("\n✓ All artifacts valid.")
    else:
        click.echo("\n✗ Some artifacts failed validation.")
        sys.exit(1)


if __name__ == "__main__":
    brief_cli()
