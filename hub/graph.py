"""Builds the dependency graph from validated service descriptors.

Resolution is by declared `id` only. Matching on names would be guesswork: two
services called `notifications` in different groups are not necessarily the same
service, and two queues spelled alike are not necessarily the same queue. An
edge pointing at an id nobody declares becomes a reported problem, not a
silently dropped line.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum

from .models import Confidence, ServiceDoc, UNKNOWN_TARGET
from .sources.base import Fetched, Problem, Severity


class NodeKind(StrEnum):
    SERVICE = "service"
    DATASTORE = "datastore"
    QUEUE = "queue"
    UNKNOWN = "unknown"


class EdgeKind(StrEnum):
    CALLS = "calls"       # service → service
    STORES = "stores"     # service → datastore
    PUBLISHES = "publishes"
    CONSUMES = "consumes"


@dataclass(slots=True)
class Node:
    id: str
    kind: NodeKind
    label: str
    purpose: str | None = None
    team: str | None = None
    lifecycle: str | None = None
    tags: list[str] = field(default_factory=list)
    #: Only set for services actually described by a descriptor. A datastore or
    #: an unresolved target is a node we inferred, not one we read.
    described: bool = False
    repo_url: str | None = None
    commit: str | None = None


@dataclass(slots=True)
class Edge:
    source: str
    target: str
    kind: EdgeKind
    confidence: Confidence
    summary: str | None = None
    via: str | None = None
    code: str | None = None
    code_url: str | None = None
    topics: list[str] = field(default_factory=list)
    #: True when `target` is not described by any collected descriptor.
    dangling: bool = False


@dataclass(slots=True)
class CollectedService:
    """A validated descriptor plus where it came from."""

    doc: ServiceDoc
    source: str
    repo: str
    repo_url: str | None
    ref: str | None
    commit: str | None


class GraphBuilder:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._problems: list[Problem] = []

    def add_problem(self, problem: Problem) -> None:
        self._problems.append(problem)

    def add_services(self, services: list[CollectedService]) -> None:
        # Two passes: every described service must exist as a node before edges
        # are resolved, otherwise resolution depends on collection order.
        for item in services:
            self._add_service_node(item)
        for item in services:
            self._add_edges(item)

    def _add_service_node(self, item: CollectedService) -> None:
        info = item.doc.service
        if info.id in self._nodes and self._nodes[info.id].described:
            self._problems.append(
                Problem(
                    severity=Severity.ERROR,
                    source=item.source,
                    repo=item.repo,
                    message=f"duplicate service id {info.id!r}",
                    detail="Two repositories declare the same id; ids must be unique.",
                )
            )
            return

        self._nodes[info.id] = Node(
            id=info.id,
            kind=NodeKind.SERVICE,
            label=info.name,
            purpose=info.purpose,
            team=info.owner.team if info.owner else None,
            lifecycle=info.lifecycle.value,
            tags=list(info.tags),
            described=True,
            repo_url=item.repo_url,
            commit=item.commit,
        )

    def _ensure_node(self, node_id: str, kind: NodeKind, label: str | None = None) -> None:
        if node_id not in self._nodes:
            self._nodes[node_id] = Node(
                id=node_id, kind=kind, label=label or node_id, described=False
            )

    def _add_edges(self, item: CollectedService) -> None:
        source_id = item.doc.service.id
        deps = item.doc.depends_on

        for dep in deps.services:
            if dep.id == UNKNOWN_TARGET:
                # An acknowledged blind spot. Kept on the map on purpose: it is
                # a question to answer, and hiding it would make the map look
                # more complete than it is.
                target = f"{UNKNOWN_TARGET}:{source_id}:{len(self._edges)}"
                self._ensure_node(target, NodeKind.UNKNOWN, "undetermined")
                dangling = False
            else:
                target = dep.id
                dangling = target not in self._nodes
                if dangling:
                    self._ensure_node(target, NodeKind.SERVICE, target)
                    self._problems.append(
                        Problem(
                            severity=Severity.WARNING,
                            source=item.source,
                            repo=item.repo,
                            message=f"{source_id} depends on undescribed service {target!r}",
                            detail="No collected repository declares this id.",
                        )
                    )

            self._edges.append(
                Edge(
                    source=source_id,
                    target=target,
                    kind=EdgeKind.CALLS,
                    confidence=dep.confidence,
                    summary=dep.summary,
                    via=dep.via,
                    code=dep.code,
                    dangling=dangling,
                )
            )

        for store in deps.datastores:
            self._ensure_node(store.id, NodeKind.DATASTORE, store.id)
            self._edges.append(
                Edge(
                    source=source_id,
                    target=store.id,
                    kind=EdgeKind.STORES,
                    confidence=store.confidence,
                    summary=store.summary,
                    via=store.kind,
                    code=store.code,
                )
            )

        for queue in deps.queues:
            self._ensure_node(queue.id, NodeKind.QUEUE, queue.id)
            kind = (
                EdgeKind.PUBLISHES
                if queue.direction.value == "publish"
                else EdgeKind.CONSUMES
            )
            self._edges.append(
                Edge(
                    source=source_id,
                    target=queue.id,
                    kind=kind,
                    confidence=queue.confidence,
                    summary=queue.summary,
                    via=queue.kind,
                    code=queue.code,
                    topics=list(queue.topics),
                )
            )

    def build(self, services: list[CollectedService]) -> dict:
        described = sum(1 for n in self._nodes.values() if n.described)
        return {
            "nodes": [asdict(n) for n in self._nodes.values()],
            "edges": [asdict(e) for e in self._edges],
            "problems": [p.as_dict() for p in self._problems],
            "stats": {
                "services": described,
                "nodes": len(self._nodes),
                "edges": len(self._edges),
                "problems": len(self._problems),
                "unresolved_edges": sum(1 for e in self._edges if e.dangling),
                "unknown_targets": sum(
                    1 for e in self._edges if e.confidence == Confidence.UNKNOWN
                ),
            },
            "services": [
                {
                    "id": s.doc.service.id,
                    "source": s.source,
                    "repo": s.repo,
                    "repo_url": s.repo_url,
                    "ref": s.ref,
                    "commit": s.commit,
                    "doc": s.doc.model_dump(mode="json"),
                }
                for s in services
            ],
        }
