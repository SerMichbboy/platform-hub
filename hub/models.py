"""Canonical models for `service.yaml`.

This module is the single source of truth for the format. The JSON Schema under
`schema/` is generated from here (`hub schema`) rather than hand-written —
otherwise the two inevitably drift apart.
"""

from __future__ import annotations

import datetime
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Confidence(StrEnum):
    """How well a dependency is backed by evidence.

    The core rule: never guess a dependency. If a service clearly calls
    *something* but the target cannot be determined, that is recorded as
    `unknown` rather than omitted or invented — an omitted edge reads as "no
    dependency", which is a different and wrong claim.
    """

    VERIFIED = "verified"  # backed by a code reference
    ASSUMED = "assumed"    # inferred from config/env, not confirmed in code
    UNKNOWN = "unknown"    # the call exists, the target is undetermined


class Coverage(StrEnum):
    """How completely a section is documented.

    Without this, an empty dependency list is indistinguishable from "this
    service has no dependencies", and a partial map reads as a complete one.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    NONE = "none"


class Lifecycle(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PLANNED = "planned"


class Direction(StrEnum):
    PUBLISH = "publish"
    CONSUME = "consume"


# `path/to/file.py` or `path/to/file.py:symbol`. Kept as a plain string rather
# than a nested object: these are written by hand in YAML, and a multi-line
# object per reference makes the file too tedious to actually maintain.
_CODE_REF = re.compile(r"^[^\s:]+(?::[A-Za-z_][\w.]*)?$")

_SERVICE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")

#: Reserved id for a dependency whose target could not be determined.
UNKNOWN_TARGET = "unknown"


class Base(BaseModel):
    # Typos in a hand-written YAML file should fail loudly, not be silently
    # dropped and leave the author thinking the field took effect.
    model_config = ConfigDict(extra="forbid")


def _validate_code_ref(value: str | None) -> str | None:
    if value is None:
        return None
    if not _CODE_REF.match(value):
        raise ValueError(
            "code reference must look like 'path/to/file.py' or "
            f"'path/to/file.py:symbol', got {value!r}"
        )
    return value


class Owner(Base):
    team: str = Field(description="Team responsible for the service")
    contact: str | None = Field(default=None, description="Who to ask about it")


class Source(Base):
    repo: str = Field(description="Repository URL")
    default_branch: str = Field(
        default="main",
        description="Only the default branch is collected — main or master",
    )
    language: str | None = None


class HttpEndpoint(Base):
    id: str = Field(description="Stable identifier for this operation within the service")
    method: str
    path: str
    summary: str
    code: str | None = Field(default=None, description="Where it is implemented")
    flow: str | None = Field(default=None, description="Path to the flow document")

    _check_code = field_validator("code")(_validate_code_ref)

    @field_validator("method")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class MessageEndpoint(Base):
    id: str
    channel: str = Field(description="Transport: rabbitmq, kafka, redis…")
    topic: str = Field(description="Queue, topic or routing key")
    direction: Direction
    summary: str
    code: str | None = None
    flow: str | None = None

    _check_code = field_validator("code")(_validate_code_ref)


class Provides(Base):
    """What the service exposes to the outside world."""

    http: list[HttpEndpoint] = Field(default_factory=list)
    messages: list[MessageEndpoint] = Field(default_factory=list)


class ServiceDep(Base):
    id: str = Field(
        description="id of another service, or 'unknown' if the target is undetermined"
    )
    via: str = Field(default="http", description="http, grpc, messages…")
    summary: str
    code: str | None = None
    confidence: Confidence = Confidence.ASSUMED

    _check_code = field_validator("code")(_validate_code_ref)


class DatastoreDep(Base):
    id: str
    kind: str = Field(description="postgres, redis, s3…")
    summary: str
    code: str | None = None
    confidence: Confidence = Confidence.ASSUMED

    _check_code = field_validator("code")(_validate_code_ref)


class QueueDep(Base):
    id: str
    kind: str = Field(description="rabbitmq, kafka…")
    topics: list[str] = Field(default_factory=list)
    direction: Direction
    summary: str | None = None
    code: str | None = None
    confidence: Confidence = Confidence.ASSUMED

    _check_code = field_validator("code")(_validate_code_ref)


class DependsOn(Base):
    """What the service depends on. The dependency map is built from this."""

    services: list[ServiceDep] = Field(default_factory=list)
    datastores: list[DatastoreDep] = Field(default_factory=list)
    queues: list[QueueDep] = Field(default_factory=list)


class Docs(Base):
    architecture: str | None = None
    flows_index: str | None = None
    changelog: str | None = None


class CoverageBlock(Base):
    http: Coverage = Coverage.NONE
    messages: Coverage = Coverage.NONE
    depends_on: Coverage = Coverage.NONE
    notes: str | None = None


class Verified(Base):
    """Which commit the description was checked against.

    Without this there is no way to tell a current description from one written
    two years and four refactors ago.
    """

    commit: str | None = None
    # `datetime.date` spelled in full: a field named `date` shadows a bare
    # `date` import inside the class body, and the annotation then fails to
    # evaluate.
    date: datetime.date | None = None


class ServiceInfo(Base):
    id: str = Field(
        description="Permanent identifier. Must not change when the service is renamed"
    )
    name: str
    purpose: str
    owner: Owner | None = None
    lifecycle: Lifecycle = Lifecycle.ACTIVE
    tags: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not _SERVICE_ID.match(v):
            raise ValueError(
                f"service id must be lowercase letters, digits and dashes, got {v!r}"
            )
        if v == UNKNOWN_TARGET:
            raise ValueError(
                f"{UNKNOWN_TARGET!r} is reserved for undetermined dependency targets"
            )
        return v


class ServiceDoc(Base):
    """Root of `docs/service/service.yaml`."""

    schema_version: int = 1
    service: ServiceInfo
    source: Source | None = None
    provides: Provides = Field(default_factory=Provides)
    depends_on: DependsOn = Field(default_factory=DependsOn)
    docs: Docs = Field(default_factory=Docs)
    coverage: CoverageBlock = Field(default_factory=CoverageBlock)
    verified: Verified = Field(default_factory=Verified)
