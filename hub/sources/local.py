"""Local source: repositories already checked out on this machine.

This is the zero-setup path — no tokens, no network — and the one worth reaching
for when adopting the hub, because the working copy is right there to check code
references against.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

from ..config import LocalSource
from .base import Fetched, Problem, Severity


def _git(repo: Path, *args: str) -> str | None:
    """Run a read-only git command, returning None if it fails for any reason."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _is_repo(path: Path) -> bool:
    return (path / ".git").exists()


class LocalReader:
    """Reads descriptors from directories on disk."""

    def __init__(self, config: LocalSource) -> None:
        self._config = config
        self.name = config.name

    def _discover(self) -> list[Path]:
        """Explicit paths first, then one level down from each configured root.

        Only one level: scanning a whole home directory recursively is slow and
        picks up vendored dependencies and build artifacts that happen to be
        git repos.
        """
        found: list[Path] = []
        seen: set[Path] = set()

        for path in self._config.expanded_paths():
            if path not in seen:
                seen.add(path)
                found.append(path)

        for root in self._config.expanded_roots():
            if not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if child.is_dir() and child not in seen and _is_repo(child):
                    seen.add(child)
                    found.append(child)

        return found

    def fetch(self, service_file: str) -> Iterator[Fetched | Problem]:
        repos = self._discover()

        if not repos:
            yield Problem(
                severity=Severity.WARNING,
                source=self.name,
                repo="-",
                message="no repositories found",
                detail="Check `roots` and `paths` in the source configuration.",
            )
            return

        for repo in repos:
            yield self._read(repo, service_file)

    def _read(self, repo: Path, service_file: str) -> Fetched | Problem:
        if not repo.is_dir():
            return Problem(
                severity=Severity.ERROR,
                source=self.name,
                repo=repo.name,
                message="path does not exist",
                detail=str(repo),
            )

        descriptor = repo / service_file
        if not descriptor.is_file():
            # Not an error: most repositories simply have not been described
            # yet. Reporting it keeps adoption progress visible.
            return Problem(
                severity=Severity.WARNING,
                source=self.name,
                repo=repo.name,
                message="no service descriptor",
                detail=f"expected {service_file}",
            )

        try:
            raw = descriptor.read_text(encoding="utf-8")
        except OSError as exc:
            return Problem(
                severity=Severity.ERROR,
                source=self.name,
                repo=repo.name,
                message="descriptor could not be read",
                detail=str(exc),
            )

        remote = _git(repo, "remote", "get-url", "origin")
        commit = _git(repo, "rev-parse", "HEAD")
        ref = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")

        return Fetched(
            source=self.name,
            repo=repo.name,
            raw=raw,
            repo_url=remote,
            ref=ref,
            commit=commit,
            # Local checkouts open in an editor rather than a browser; the web
            # URL for a private host is not knowable from here.
            code_url_template=f"file://{repo}/{{path}}",
        )
