# Initial release technical design

Label: wayfinder:map
Status: resolved

Authority: historical resolved design rationale, not an active implementation
queue. Its decisions remain requirement inputs; its old next-action/status text
is historical. Use the [authoritative product-completion backlog](../product-completion/ticket-plan.md)
for remaining work. Implementation remains paused pending explicit authorization.

## Destination

A build-ready first-release design for the statement-import and financial
dashboard application: chosen technology/deployment, persistence, worker
contracts, financial rules, operations, and agreed public test interfaces.
Hand off to `/to-spec`, then `/to-tickets`; this map does not implement the app.

## Notes

- The approved product/logical baseline is
  [HLD v0.3](../../beng-document-intelligence-hld.md). Retain its scope and
  decisions; do not repeat the product interview.
- Latest user direction supersedes its storage placement: authoritative state
  on mini-PC local storage; NAS is backup/archive only. See the active
  [storage decision](issues/06-authoritative-storage-acceptance-backup.md).
  Historical transaction records and active originals stay local; twelve months
  is a default dashboard view, not automatic deletion. Nightly consistent NAS
  backups and loss since last successful backup are accepted; backup failures
  remain visible and do not stop normal use. PostgreSQL Docker on the mini-PC
  and seven successful nightly generations are selected; exact restore commands
  remain implementation work under the agreed recovery contract.
  Do not imply moving hosts eliminates power-loss or backup risk.
- Performance acceptance is agreed in
  [Public test interfaces and release acceptance](issues/12-public-test-interfaces-and-release-acceptance.md).
  Actual hardware feasibility remains unmeasured.
- Follow [AGENTS.md](../../AGENTS.md) and
  [local tracker conventions](../../docs/agents/issue-tracker.md).
- Deployment constraint added by Sourav: project application, worker and database
  use Docker containers; native deployment only as an explicitly discussed,
  very simple exception. Existing vendor services remain separate.
- Decision sessions use `grilling` and `domain-modeling`; research uses the
  `research` skill and primary sources. Use `codebase-design` for interfaces
  and `prototype` only where a concrete artifact is needed to settle a question.
- Sourav supplies all four representative account formats before implementation.
  Formats block their dependent decisions, not all planning. Keep private
  statements and secrets out of this tracker and Git.
- Sources distinguish observed local configuration, user reports, documentation,
  proposals, and real-host verification. Documentation is not deployment proof.
- Open decisions are the child files in `issues/`; discover the frontier from
  their Status and Blocked by fields. Resolve one non-research ticket per
  session; research tickets may proceed independently in parallel.
- User push restrictions override research-branch publishing defaults: no push
  without a completed milestone and explicit approval. Initial research notes
  stay local in this effort's `research/` directory; no branch publishing.

## Decisions so far

- [Public test interfaces and release acceptance](issues/12-public-test-interfaces-and-release-acceptance.md): four public test seams, independent fixtures/private-source verification, measured p95 latency target and real-host release/recovery gates approved; no test execution claimed.

- [Local interpretation contract and model evaluation](issues/11-local-interpretation-and-model-evaluation.md): optional confirmed classification advice, graceful failure and bounded two-candidate laptop evaluation agreed; quality/coverage/time gates set, exact model unselected until tested, deterministic release can proceed without advice.

- [Dashboard evidence and review interactions](issues/10-dashboard-and-review-interactions.md): shared periods and metric drill-down, dated account evidence/gap-aware graphs, explicit single-issue review with correction history, and core phone/desktop flows agreed; visual implementation remains later work.

- [Import, matching, and financial rule contracts](issues/07-import-matching-financial-rules.md): personal/savings GBP Revolut scope, conversion/cash/reversal semantics, account mapping, intake limits and reconciliation gates accepted; conservative matching and invented examples recorded for specification/tests.

- [Representative account formats and expected facts](issues/04-representative-account-formats.md): four text PDFs received and inspected; format inventory and selected arithmetic checks captured, with card-period, multi-account and fixture gaps explicit.

- [Private access, batching, and operating policy](issues/09-private-access-and-operations.md): private HTTPS/login, scoped worker credentials, 21:00 processing/03:00 backups Europe/London, ten-minute readiness limit, visible failures, safe logs and crash/reboot recovery agreed; deployment integration remains untested.

- [Worker jobs, retries, and result publication](issues/08-worker-job-and-result-contract.md): API-only serial jobs, fenced retries, idempotent publication, protected corrections and bounded existing-controller keep-awake leases agreed; lifecycle integration remains untested.

- [Application stack and deployment choice](issues/05-application-deployment-choice.md): Django/Python and a custom rendered UI selected; Mac development/local tests followed by actual-host milestone E2E; local runtime setup remains open.
- [Authoritative storage, acceptance, and backup](issues/06-authoritative-storage-acceptance-backup.md): mini-PC local PostgreSQL/originals, retained history, and seven successful nightly NAS recovery sets agreed; host durability and restore tests remain required.
- [Host, storage, and wake inventory](issues/01-host-storage-wake-inventory.md): all three aliases verified; NAS/laptop hardware and runtime inspected; existing wake route is programmatically callable, actual wake untested.
- [Database durability and NAS storage evidence](issues/02-database-durability-research.md): documented storage/transaction/backup guarantees and their limits established; architecture remains open.
- [Application and worker stack evidence](issues/03-application-stack-research.md): two practical stacks compared; Python-first candidate identified, final selection pending host facts and discussion.

## Not yet specified

No further policy decisions remain open in this map. Unknown layouts and
unproven matches follow the agreed rejection/review rules; new evidence that
changes scope or policy requires a new explicit decision, not a silent assumption.

## Handoff to specification

All twelve child tickets are resolved. The
[first-release specification](../initial-release/spec.md) synthesizes the HLD and
linked decisions. Next create end-to-end implementation/test tickets from that
specification; application implementation has not started.
Keep the following work explicit rather than claiming a deployment-ready system:

- Choose/prepare the Mac test runtime before real PostgreSQL tests require it;
  specify schema, API/result contracts and safe original/record preservation.
- Pin supported parser layouts and create synthetic/sanitized fixtures plus
  independently reviewed expected facts; preserve private originals outside Git.
- Specify private hostname/TLS/routing, worker/controller credentials and the
  controller adapter; verify the production Docker endpoint, storage headroom
  and user-supplied local/NAS paths before provisioning.
- Calibrate claim/retry/execution timing and verify DST/catch-up, lease ceilings,
  restart recovery, consistent backup/restore, private access and device behavior.
- Carry the bounded two-candidate laptop evaluation as a prerequisite before
  enabling advice. Exact model/runtime selection remains open until tested;
  the deterministic application may ship with manual review.

No application implementation, installation or deployment has been performed.
Follow the approved TDD seams and milestone evidence gates. A completed planning
milestone does not authorize a Git push.

## Out of scope

- Application implementation, deployment, and data migration within this map.
- Reopening the approved product scope without an explicit user change.
- General document parsing, OCR, other ingestion channels, multi-user support,
  cloud AI, FX conversion, detailed spending categories, and deep search.
- New queue/search services, forced laptop sleep, or elaborate backup systems.
- Off-NAS backup infrastructure and pushing research branches without approval.
- NAS-hosted project database or project compute, following the placement change.
