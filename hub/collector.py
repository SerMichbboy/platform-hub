"""Collection pipeline: fetch → validate → resolve → graph."""

from __future__ import annotations

from datetime import UTC, datetime

import yaml
from pydantic import ValidationError

from .config import GitHubSource, GitLabSource, HubConfig, LocalSource
from .graph import CollectedService, GraphBuilder
from .models import ServiceDoc
from .sources.base import Fetched, Problem, Severity, Source
from .sources.local import LocalReader


def build_source(config: LocalSource | GitLabSource | GitHubSource) -> Source:
    if isinstance(config, LocalSource):
        return LocalReader(config)
    raise NotImplementedError(
        f"source type {config.type.value!r} is not implemented yet; "
        "only 'local' is available in this version"
    )


def _format_validation_error(exc: ValidationError) -> str:
    lines = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "(root)"
        lines.append(f"{location}: {error['msg']}")
    return "; ".join(lines)


def parse_descriptor(item: Fetched) -> CollectedService | Problem:
    """Turn raw YAML into a validated descriptor, or an explicit problem."""
    try:
        data = yaml.safe_load(item.raw)
    except yaml.YAMLError as exc:
        return Problem(
            severity=Severity.ERROR,
            source=item.source,
            repo=item.repo,
            message="descriptor is not valid YAML",
            detail=str(exc),
        )

    if not isinstance(data, dict):
        return Problem(
            severity=Severity.ERROR,
            source=item.source,
            repo=item.repo,
            message="descriptor is empty or not a mapping",
        )

    try:
        doc = ServiceDoc.model_validate(data)
    except ValidationError as exc:
        return Problem(
            severity=Severity.ERROR,
            source=item.source,
            repo=item.repo,
            message="descriptor does not match the schema",
            detail=_format_validation_error(exc),
        )

    return CollectedService(
        doc=doc,
        source=item.source,
        repo=item.repo,
        repo_url=item.repo_url,
        ref=item.ref,
        commit=item.commit,
    )


def collect(config: HubConfig) -> dict:
    """Run every configured source and assemble a single graph."""
    builder = GraphBuilder()
    services: list[CollectedService] = []

    for source_config in config.sources:
        try:
            source = build_source(source_config)
        except NotImplementedError as exc:
            builder.add_problem(
                Problem(
                    severity=Severity.ERROR,
                    source=source_config.name,
                    repo="-",
                    message="source type unavailable",
                    detail=str(exc),
                )
            )
            continue

        for item in source.fetch(config.service_file):
            if isinstance(item, Problem):
                builder.add_problem(item)
                continue

            parsed = parse_descriptor(item)
            if isinstance(parsed, Problem):
                builder.add_problem(parsed)
            else:
                services.append(parsed)

    builder.add_services(services)
    result = builder.build()
    result["generated_at"] = datetime.now(UTC).isoformat()
    result["service_file"] = config.service_file
    return result
