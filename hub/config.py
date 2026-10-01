"""Hub configuration: which repositories to collect, and how to reach them.

The real config (`hub.config.yaml`) is gitignored because it describes a private
topology. Tokens are never stored here — only the *name* of the environment
variable holding one, so the config itself stays safe to share or paste.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

#: Conventional location of the service descriptor inside a repository.
DEFAULT_SERVICE_FILE = "docs/service/service.yaml"


class SourceType(StrEnum):
    LOCAL = "local"
    GITLAB = "gitlab"
    GITHUB = "github"


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TokenMixin(Base):
    token_env: str | None = Field(
        default=None,
        description="Name of the env var holding the access token. Never the token itself.",
    )

    def token(self) -> str | None:
        return os.environ.get(self.token_env) if self.token_env else None


class LocalSource(Base):
    """Repositories already checked out on this machine.

    The fastest way to try the hub: no tokens, no network, and the working copy
    is right there to verify code references against.
    """

    type: Literal[SourceType.LOCAL] = SourceType.LOCAL
    name: str = "local"
    roots: list[Path] = Field(
        default_factory=list,
        description="Directories to scan one level deep for repositories",
    )
    paths: list[Path] = Field(
        default_factory=list, description="Explicit paths to individual repositories"
    )

    def expanded_roots(self) -> list[Path]:
        return [p.expanduser().resolve() for p in self.roots]

    def expanded_paths(self) -> list[Path]:
        return [p.expanduser().resolve() for p in self.paths]


class GitLabSource(TokenMixin):
    type: Literal[SourceType.GITLAB] = SourceType.GITLAB
    name: str = "gitlab"
    host: str = Field(default="https://gitlab.com", description="GitLab base URL")
    projects: list[str] = Field(
        default_factory=list, description="Project paths, e.g. 'group/service-a'"
    )
    groups: list[str] = Field(
        default_factory=list,
        description="Groups to enumerate; every project inside is considered",
    )


class GitHubSource(TokenMixin):
    type: Literal[SourceType.GITHUB] = SourceType.GITHUB
    name: str = "github"
    api_url: str = "https://api.github.com"
    repos: list[str] = Field(
        default_factory=list, description="Repositories, e.g. 'owner/service-a'"
    )
    orgs: list[str] = Field(
        default_factory=list, description="Organisations to enumerate"
    )


SourceConfig = Annotated[
    LocalSource | GitLabSource | GitHubSource, Field(discriminator="type")
]


class HubConfig(Base):
    service_file: str = Field(
        default=DEFAULT_SERVICE_FILE,
        description="Path to the service descriptor within each repository",
    )
    sources: list[SourceConfig] = Field(default_factory=list)
    output: Path = Field(
        default=Path("build/hub.json"), description="Where the collected graph is written"
    )

    @classmethod
    def load(cls, path: Path) -> HubConfig:
        if not path.exists():
            raise FileNotFoundError(
                f"config not found: {path}\n"
                "Copy hub.config.example.yaml to hub.config.yaml and edit it."
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)
