# Issue tracker: Local Markdown

Specs, implementation tickets, and design decision maps live in `.scratch/`.
These are version-controlled project artifacts, unlike local `.agent/` memory.

## Implementation work

- One feature or milestone per `.scratch/<feature-slug>/` directory.
- Spec: `spec.md`.
- Tickets: `issues/<NN>-<slug>.md`, numbered from `01` in dependency order.
  Use one file per ticket, never one combined tickets file.
- Each ticket describes end-to-end behavior, acceptance criteria, dependencies,
  and relevant verification. Use the domain glossary's vocabulary.
- Record `Status:` near the top using `triage-labels.md`.
- Record dependencies as `Blocked by: NN, NN`, or `None`.
- Claim work by recording `Claimed by:` before implementation. A ticket is
  available when it is ready, unclaimed, and all blockers are `done`.
- Work the available tickets in dependency order; lowest available number first.
- Append discussion under `## Comments`.
- After acceptance checks pass, record verification evidence and implementation
  commit references when available, set `Status: done`, and clear the claim.
- Mark a spec done only when all its tickets and milestone acceptance checks
  are complete. Record remaining verification limits explicitly.

## Skill operations

- "Publish": create the corresponding local Markdown file.
- "Fetch": read the referenced file. Resolve bare numbers within the named
  feature; ask if the reference could identify more than one ticket.
- "Close": update the local status and record completion evidence.
- GitHub hosts the Git repository. Do not create GitHub Issues for this
  workflow unless the user changes the tracker.

## Wayfinding operations

- Map: `.scratch/<effort>/map.md`, containing Destination, Notes, Decisions so
  far, Not yet specified, and Out of scope.
- Decision tickets: `.scratch/<effort>/issues/<NN>-<slug>.md`, numbered from `01`.
- Each decision ticket records its question, `Type:` (`research`, `prototype`,
  `grilling`, or `task`), `Status: open`, and `Blocked by:`.
- A decision is available when it is open and all blockers are `resolved`.
  Lowest available number first.
- Claim: set `Status: claimed` before work; record the claimant when needed.
- Resolve: append `## Answer`, set `Status: resolved`, then add a brief linked
  pointer in the map's Decisions so far.
- Keep decision efforts separate from implementation feature directories.
  Wayfinding tickets use decision lifecycle states, not triage labels.
- Refer to maps and tickets by linked title in user-facing updates.

## Commits and pushes

Follow `AGENTS.md` for commit authorization and milestone push approval.
Closing a ticket or publishing a map does not authorize a push.
