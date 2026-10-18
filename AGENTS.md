# Project instructions

## Persistent workflow memory

Before substantive work, use $workflow-guide. Resume an existing `.agent/`;
if none exists, ask whether to enable persistent agent orchestration before
creating it.

Treat `.agent/` as local working memory. Never stage, commit, or push it.

## Design and implementation

- Read `beng-document-intelligence-hld.md` before design or implementation.
  It defines the agreed initial scope; keep its open decisions explicit.
- Initial scope is Sourav's statement-import and financial-dashboard app.
  General household documents, OCR, multi-user support, and deep search are
  future scope, not implicit implementation requirements.
- Before implementation starts, ask Sourav for representative Lloyds Current,
  Lloyds Credit, Amex Credit, and Revolut Debit formats. Planning may continue
  meanwhile; do not invent layouts or sample-dependent matching rules.
- Resolve consequential design questions with the user before implementation.
  Distinguish requirements, proposals, assumptions, and verified facts.
- Preserve originals, source evidence, processing history, and corrections.
  Apply the HLD's financial reporting semantics; keep uncertainty visible.
- Use deterministic parsing and validation for financial facts. Local LLM
  output is advisory; no cloud AI or silent replacement of source facts.
- Keep normal use independent of laptop availability. The mini-PC application
  owns authoritative updates; the laptop worker obtains jobs and returns
  results through its API. Authoritative state uses mini-PC local storage;
  the NAS is a backup/archive destination, not live database storage or compute.
  Keep active originals and imported transaction history local. Twelve months is
  a dashboard default, not a deletion rule; NAS backup failure does not stop
  normal use or authorize local deletion. See HLD v0.3 for the recovery window.
- Use clear internal modules within one application and one worker. Add
  abstractions or services only for concrete requirements.
- Deploy project application, worker, and database in Docker containers.
  Native deployment is an exception only when demonstrably very simple;
  raise the exception with Sourav before choosing it. Existing native vendor
  or infrastructure services are not permission to deploy project code natively.
- Build approved tickets as end-to-end slices including their tests.
- Use TDD at public interfaces agreed with the user: observe a failing
  behavioral test, implement the minimum needed, then repeat.
- Review changes against the ticket and project standards before completion.

## Verification and safety

- Run checks appropriate to each change and record commands and results.
- Before declaring a milestone complete, verify its acceptance criteria and
  report untested requirements. Distinguish local tests from real-host evidence.
- Use synthetic or sanitized fixtures with independently established expected
  results. Keep real private statements, credentials, and secrets out of Git.
- Preserve unrelated user changes. Obtain explicit approval for destructive
  operations, deployment, or migrations affecting existing data.

## Git permissions

- Create local commits as needed for coherent, verified changes without
  requesting approval each time.
- Stage explicit paths and inspect the staged diff before committing.
- Include local specs and tickets in version control; keep `.agent/` local.
- Push only after a milestone is complete AND the user explicitly approves
  that push. Milestone completion alone does not authorize pushing.
- Use direct pushes; pull requests are not required.
- Never force-push or rewrite published history without explicit approval.

## Agent skills

### Issue tracker

Local Markdown specs and tickets live under `.scratch/`. Before creating,
reading, claiming, or closing work, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage roles as local ticket status values. Before
triaging work, read `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: root `GLOSSARY.md` and `docs/adr/`. Before design,
exploration, or implementation, read `docs/agents/domain.md`.
