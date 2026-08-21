# Capability Contract — v1.0.0

The one frozen artifact in forge. Every capability conforms to it. It evolves only by weakening what it demands of capabilities or strengthening what it guarantees them; nothing is deleted, only deprecated.

## A capability is

A directory under `.claude/skills/<name>/` containing at minimum:

```
.claude/skills/<name>/
├── manifest.yaml     # cheap static metadata — the only part always visible
├── SKILL.md          # the procedure — loaded only when triggered
└── references/       # optional depth — loaded only when SKILL.md points to it
```

Loading is lazy at every layer. A capability's body must never be needed to decide whether the capability is relevant — the manifest alone decides that.

## manifest.yaml

```yaml
name: <kebab-case>          # unique
version: <semver>
need: >                     # the recurring need this serves, one sentence.
                            # A capability whose need no longer occurs is deprecated.
triggers:                   # when it activates
  - <phrase or event or schedule>
context:
  loads: <what it reads, and when>
  never: <what it must not load>
contract:
  pre: [<what must be true before it runs>]      # violation = caller's defect
  post: [<what it guarantees when it completes>] # violation = capability's defect
  invariants: [<what it may never corrupt>]      # e.g. user data, kernel, git history
verifier: >                 # what grades the output — never the producer itself
reports: sbar               # report shape: situation, background, assessment, recommendation
evolution:
  signals: [<usage signals that should trigger revision or deprecation>]
```

Each pre/postcondition is checked by exactly one side — no defensive double-checking.

## Uniform conventions (kernel-imposed)

- **Naming**: kebab-case names; verbs for capabilities that act (`validate`, `reflect`), nouns for ones that hold knowledge.
- **Failure**: fail loudly and as early as possible. No capability silently degrades, retries indefinitely, or swallows an error.
- **Reporting**: decision-first (situation, change, assessment, ask). Reports and durable state go to files/git — never only to the conversation.
- **Isolation**: capabilities do not read each other's internals; they compose through artifacts and the kernel's conventions.
- **Scope**: one need per capability. A new job means a new capability, not a feature added to an old one.
- **Output separation**: capability output (records, reports, generated data) never enters a framework repo — framework repos carry mechanism only. Outputs live in the session workspace and in owner-designated private data stores.

## Lifecycle

**Propose** (a repeated need with no capability — usually surfaced by the loop) → **scaffold** from `contract/template/` → **use** → **evolve** (reviewed diffs, semver) → **deprecate** (need gone; manifest marked, body retained one major version) → **delete** (next major version only).

## What the contract does NOT govern

Kernel internals and stack template contents may change freely and are not part of any capability's observable surface. Do not depend on them.
