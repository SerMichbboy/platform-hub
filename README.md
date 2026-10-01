# platform-hub

A service catalogue and dependency map assembled from the repositories
themselves — so that "it's called somewhere around here" finally gets a precise
address.

Each repository describes itself in one `docs/service/service.yaml`. The hub
reads those files across every repository you point it at, resolves the
dependencies between them, and produces a single map — for people to read and
for coding agents to query.

> **Status: early.** The schema, validator, local collector and graph builder
> work. The web UI and the GitLab/GitHub connectors are next. See
> [Roadmap](#roadmap).

## Why

Service documentation decays because it lives away from the code. The usual
result is a wiki page that was accurate two refactors ago, and a dependency
diagram somebody drew by hand once.

platform-hub inverts that: the description lives **in the repository**, next to
the code it describes, reviewed in the same merge request. The hub never stores
its own copy to edit — it only ever reads.

## Design principles

These are what make the map trustworthy, and they are enforced by the schema:

**Never guess a dependency.** If a service calls *something* and the target
cannot be established, it is recorded as `confidence: unknown` and stays visible
on the map as an open question. An omitted edge would read as "no dependency" —
a different and wrong claim.

**Incomplete is fine; pretending to be complete is not.** Every descriptor
carries a `coverage` block. Without it an empty dependency list is
indistinguishable from "this service has no dependencies".

**Names do not establish identity.** Dependencies resolve by declared `id` only.
Two services called `notifications` in different groups are not the same
service; two queues spelled alike are not the same queue. An edge pointing at an
id nobody declares is reported as a dangling reference, not quietly dropped.

**Problems are output, not exceptions.** A repository that is unreachable or has
no descriptor appears *in the result* as a known gap. One bad repository never
kills a collection run, and never silently shrinks the map.

**Claims are dated.** `verified.commit` and `verified.date` record which commit
a description was checked against, so a current description is distinguishable
from one written long before four refactors.

## Quick start

```bash
pip install -e .

cp hub.config.example.yaml hub.config.yaml   # gitignored; edit to taste
hub collect
```

Out of the box the example config points at two bundled services, which
deliberately include a dangling reference and an undetermined target:

```
collected 2 service(s), 7 edge(s) → build/hub.json

1 problem(s), 0 error(s):
 - [checkout] checkout depends on undescribed service 'legacy-crm'
```

Validate descriptors without collecting:

```bash
hub check path/to/repo          # or a directory of repositories
```

Regenerate the JSON Schema after changing the models:

```bash
hub schema                      # writes schema/service.schema.json
```

Point your editor at `schema/service.schema.json` for completion and inline
validation while writing `service.yaml`.

## Configuration

`hub.config.yaml` is gitignored — it describes a private topology. Tokens are
referenced by environment variable name and never written into the file.

```yaml
service_file: docs/service/service.yaml
output: build/hub.json

sources:
  - type: local
    name: workspace
    roots: [~/projects]          # every git repo one level down

  - type: gitlab                 # planned
    host: https://gitlab.example.com
    token_env: GITLAB_TOKEN
    groups: [my-group]
```

The `local` source needs no tokens and no network, which makes it the easiest
way to try the hub against repositories you already have checked out.

## The descriptor

```yaml
service:
  id: checkout                   # permanent; survives renames
  name: Checkout
  purpose: Accepts orders, reserves stock and starts payment.
  owner: { team: commerce }

provides:
  http:
    - id: create-order
      method: POST
      path: /api/v1/orders
      summary: Create an order and start payment.
      code: src/api/orders.py:create_order

depends_on:
  services:
    - id: billing
      summary: Charges the customer for a new order.
      code: src/clients/billing.py:charge
      confidence: verified

coverage:
  depends_on: partial
  notes: Background jobs are not described yet.

verified:
  commit: a1b2c3d
  date: 2026-10-01
```

See [`examples/`](examples/) for complete, annotated descriptors and
[`schema/service.schema.json`](schema/service.schema.json) for every field.

## Roadmap

- [x] Schema, validator, graph builder
- [x] Local collector
- [ ] Web UI: map, search, service cards, code links
- [ ] GitLab and GitHub connectors
- [ ] MCP server, so coding agents can query the catalogue directly
- [ ] Optional metrics overlay (traffic, errors, latency)

## Prior art

[Spotify Backstage](https://backstage.io) pioneered this shape — a
`catalog-info.yaml` per repository feeding a central catalogue — and is the
right answer for an organisation that wants a full developer portal with a
plugin ecosystem.

platform-hub is deliberately much smaller: a CLI and a static graph you can
point at a handful of repositories in an afternoon, with coding agents as a
first-class consumer rather than an afterthought.

## License

MIT — see [LICENSE](LICENSE).
