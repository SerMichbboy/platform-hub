"""Source interface: everything the collector needs to read a repository.

A source yields `Fetched` records and `Problem` records side by side. Problems
are deliberately part of the normal return value rather than raised: a repo that
is unreachable, or has no descriptor, must show up *in the hub* as a known gap.
If it were an exception the collector would either die on one bad repo or, worse,
swallow it and present an incomplete map as a complete one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterator, Protocol, runtime_checkable


class Severity(StrEnum):
    ERROR = "error"      # nothing usable was collected
    WARNING = "warning"  # collected, but incomplete or suspect


@dataclass(slots=True)
class Problem:
    """Something the hub could not do, surfaced to the user instead of hidden."""

    severity: Severity
    source: str
    repo: str
    message: str
    detail: str | None = None

    def as_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "source": self.source,
            "repo": self.repo,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass(slots=True)
class Fetched:
    """A raw service descriptor plus the provenance needed to trust it."""

    source: str
    repo: str
    raw: str
    repo_url: str | None = None
    ref: str | None = None
    commit: str | None = None
    #: Template for linking a repo-relative path to a viewable location.
    #: Supports `{path}`, `{commit}`, `{ref}`.
    code_url_template: str | None = field(default=None, repr=False)

    def code_url(self, path: str) -> str | None:
        """Build a link to `path` inside this repo, if the source supports it."""
        if not self.code_url_template:
            return None
        return self.code_url_template.format(
            path=path.lstrip("/"),
            commit=self.commit or self.ref or "HEAD",
            ref=self.ref or "HEAD",
        )


@runtime_checkable
class Source(Protocol):
    """Reads service descriptors out of some collection of repositories."""

    name: str

    def fetch(self, service_file: str) -> Iterator[Fetched | Problem]:
        """Yield one record per repository considered.

        Implementations must yield a `Problem` for every repository they looked
        at but could not read — silence here becomes a blank spot on the map.
        """
        ...
