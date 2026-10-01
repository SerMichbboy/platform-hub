# Adding a service to the hub

What this costs you: **one YAML file per repository.** Nothing else is required,
nothing is moved out of your repo, and the hub never writes back to it.

## Start smaller than feels right

The usual way a service catalogue dies is demanding a complete, perfect
description before a repository is allowed in. Nobody has an afternoon for that,
so nobody does it, and the catalogue stays empty.

This hub is built to accept partial descriptions on purpose. A descriptor with a
name, a purpose and three honest words in `coverage` is already useful — it puts
the service on the map and makes the gaps visible. Fill in the rest when you
next touch that area of the code.

## 1. Create the descriptor

Copy the template into your repository:

```bash
mkdir -p docs/service
curl -o docs/service/service.yaml \
  https://raw.githubusercontent.com/<owner>/platform-hub/main/docs/templates/service.yaml
```

Fill in the identity block first — it is the only part that is genuinely hard to
change later:

```yaml
service:
  id: checkout          # permanent. Pick carefully; everything references it.
  name: Checkout
  purpose: Accepts orders, reserves stock and starts payment.
  owner:
    team: commerce
```

**About `id`.** It is the primary key of the whole map. Other services reference
this service by it, so renaming it later breaks their descriptors. Choose
something that describes the *responsibility*, not the current repository name
or framework — `checkout`, not `checkout-service-v2` or `django-checkout`. It
should survive a rewrite.

## 2. Describe what the service exposes

List the entry points that other things actually depend on. Each gets a code
reference so a reader can confirm it rather than trust it:

```yaml
provides:
  http:
    - id: create-order
      method: POST
      path: /api/v1/orders
      summary: Create an order and start payment.
      code: src/api/orders.py:create_order

  messages:
    - id: order-created
      channel: rabbitmq
      topic: orders.created
      direction: publish
      summary: Emitted once an order is persisted.
      code: src/events/publisher.py:publish_order_created
```

Code references are `path/to/file.py` or `path/to/file.py:symbol`, relative to
the repository root.

## 3. Describe what it depends on

This is the part that builds the map, and the part where honesty matters most.

```yaml
depends_on:
  services:
    - id: billing
      via: http
      summary: Charges the customer for a new order.
      code: src/clients/billing.py:charge
      confidence: verified

  datastores:
    - id: postgres-checkout
      kind: postgres
      summary: Orders and reservations.
      code: src/infrastructure/db/engine.py

  queues:
    - id: rabbitmq-main
      kind: rabbitmq
      topics: [orders.created]
      direction: publish
```

**Set `confidence` truthfully:**

| | |
|---|---|
| `verified` | You followed the code and confirmed it |
| `assumed` | You inferred it from config or environment but did not confirm |
| `unknown` | The call demonstrably happens; the target is not established |

**Never leave out a dependency you cannot pin down.** Write it with
`id: unknown` and `confidence: unknown`:

```yaml
    - id: unknown
      via: http
      summary: Outbound webhook to a partner endpoint read from configuration.
      code: src/clients/partner.py:notify
      confidence: unknown
```

Omitting it would state "there is no such dependency", which is a different and
false claim. Recorded this way it stays on the map as an open question — which
is the honest representation, and often the thing that turns out to matter.

**Shared infrastructure must agree on ids.** If two services use the same
database or queue, both must spell the id identically — that identical id is the
*only* thing that joins them on the map. The hub deliberately will not merge
`rabbitmq-main` and `rabbitmq_main` for you, because similar names are not
evidence of a shared resource. Agree on the names once, write them down.

## 4. State your coverage

```yaml
coverage:
  http: complete
  messages: partial
  depends_on: partial
  notes: Background jobs are not described yet.

verified:
  commit: a1b2c3d
  date: 2026-10-01
```

Without this block an empty list is ambiguous: a reader cannot tell "this
service has no message handlers" from "nobody wrote them down yet". `partial`
with a note is a perfectly respectable state to be in for a long time.

## 5. Validate before committing

```bash
hub check .
```

```
ok   docs/service/service.yaml

1/1 valid
```

The validator rejects mistyped keys rather than ignoring them, so a `htpp:`
typo fails loudly instead of silently describing nothing.

## 6. Register it with the hub

In your `hub.config.yaml` (gitignored — it describes a private topology):

```yaml
sources:
  - type: local
    name: workspace
    roots: [~/projects]      # picks up every git repo one level down
```

Then:

```bash
hub collect
```

```
collected 3 service(s), 11 edge(s) → build/hub.json

2 problem(s), 0 error(s):
 - [checkout] checkout depends on undescribed service 'legacy-crm'
 - [reporting] no service descriptor (expected docs/service/service.yaml)
```

**Read the problems — they are the point, not noise.** The first line says
`checkout` points at something nobody has described; either describe it or the
map has a hole. The second says a repository has not been onboarded yet. The
problem list is how you track adoption.

## 7. Keep it from rotting

Documentation decays when updating it is a separate task that can be skipped.
Three habits prevent that:

- **Change behaviour and description in the same merge request.** A new endpoint
  and its `provides.http` entry belong in one diff, reviewed together.
- **Run `hub check` in CI.** It is fast and needs no configuration, so a broken
  descriptor fails the build like any other error.
- **Update `verified` when you re-check.** It is what separates a current
  description from one that merely looks current.

A minimal CI step:

```yaml
- run: pip install platform-hub && hub check .
```

## Growing beyond one file

Once the descriptor is in place, these are worth adding — in this order, and
only when the service is complex enough to need them:

| | |
|---|---|
| `docs/service/architecture.md` | How the service is built and why |
| `docs/service/flows/<scenario>.md` | How one operation runs end to end |
| `docs/CHANGELOG.md` | What changed, by version |

A flow document answers five questions: what is required to start, what happens
in what order, what data changes and when it is persisted, what happens on
failure or retry, and where the code and its tests live.

Point to them from the descriptor so the hub and any agent can find them:

```yaml
docs:
  architecture: docs/service/architecture.md
  flows_index: docs/service/flows/README.md
```

## Common mistakes

**Encoding the stack into the id.** `id: checkout`, not `id: fastapi-checkout`.
The id outlives the framework.

**Marking everything `verified` by reflex.** `confidence` is only worth
recording if it is accurate; blanket `verified` makes the field meaningless and
quietly removes the signal that a dependency needs checking.

**Describing endpoints nobody calls.** Document what is actually depended upon.
An exhaustive list of every route is harder to maintain and no more useful.

**Waiting until it is complete.** A `partial` descriptor merged today beats a
complete one that never gets written.
