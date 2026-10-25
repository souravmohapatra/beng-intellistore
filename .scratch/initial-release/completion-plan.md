# Product completion plan

Authority: RETIRED — historical audit and approved task proposal. The [product-completion backlog](../product-completion/ticket-plan.md) is now the sole active implementation direction; its [specification](../product-completion/spec.md) owns current gates. Text below records the proposal at approval time, not a second queue. Implementation remains paused.
Owner: coding assistant as project manager and technical lead; Sourav owns product acceptance and consequential trade-offs.
Baseline: setup commit `079e96d`, existing [spec](spec.md), [ticket plan](ticket-plan.md), HLD and ADRs. This plan reconciles delivery; it does not replace accepted financial semantics or silently close tickets.

## 1. Destination

A usable personal statement application, not merely running containers: Sourav can set up named accounts in the product, import supported statements, understand source-backed dashboard figures, review uncertainty and local model suggestions, recover from worker failures, and restore a verified backup. Normal browsing must not require the laptop or NAS.

Completion includes local inference integration and actual-laptop qualification. Sourav approved this boundary, superseding automatic deterministic-only completion: if both candidates fail, report results and obtain an explicit scope decision. Preserve deterministic financial extraction and confirmation-before-classification-change regardless of model choice.

## 2. Evidence-backed status

Evidence categories: **local implementation**, **host observation**, **user-reported installation**, **missing delivery**, **unverified acceptance**. These are not interchangeable. No percentage-complete claim is meaningful from ticket counts or test count alone.

| Capability | Actual status | Remaining delivery / acceptance |
| --- | --- | --- |
| App/database/worker deployment | Scripts committed; Sourav reports setup completed on both machines. Screenshot shows signed-in deployed overview. Read-only GET to deployed login succeeded. | Record deployed revisions/configuration and a supported-statement end-to-end result; installation is not release acceptance. |
| Named accounts and onboarding | Account model/admin exist; fresh product shows no accounts. | Product-level account creation and clear first-upload guidance; admin must not be the routine user workflow. Proposed explicit addition/clarification to 01/23. |
| Four source families and financial reporting | Tickets 05,07–17 record local deterministic parser/reporting/review/matching implementation and synthetic evidence. | Actual supplied-source accuracy against independent private expected results; preserve limits on Revolut sections and savings coverage. Do not rebuild working financial logic. |
| Web UI | HTML pages and functional forms exist. `templates/base.html` has no stylesheet; user screenshot confirms browser-default presentation. Period/history evidence exists, including an SVG chart. | Designed responsive dashboard, upload/status, transaction/evidence, search and review experiences; keyboard/accessibility, actual phone and desktop acceptance. Ticket23 not started. Not just adding a stylesheet. |
| Worker scheduling/wake/recovery | 20 locally complete; 18/21 have substantial tested implementation. Read-only host query: worker service active. | Target timing, wake/readiness, lease lifecycle/expiry/cap, crash/restart and suspend/resume acceptance. No live power/fault actions performed for this audit. |
| Publication/corrections | Existing idempotence/fencing/correction mechanisms; 19 remains open, not an absent subsystem. | Lost-ack replay, conflicting payload, stale attempts, concurrent user edits and changed-identity reprocessing must be demonstrated through public interfaces. |
| Local LLM inference | Tickets27/28 not started; parser worker has no integrated advisory path. Host Ollama service active; RTX2070 Max-Q reports8192MiB; `/api/tags` lists `gemma4:latest`,8B,Q4_K_M,artifact~9.61GB. | Adapter, versioned structured suggestions/provenance, user confirmation/rejection, separate bounded advice retries, runtime/container connectivity, model pinning and held-out evaluation. Installed model is not a selected/qualified model; artifact size does not establish VRAM fit. No inference was run. |
| Operational visibility/privacy | Some upload/readiness state exists; ticket22 unfinished. | Coherent visible failures, last-success times, worker/advice/backup state and sanitized diagnostics; runtime-up and model-ready must remain distinct. |
| NAS backup/restore | Tickets24/25 not started. | Consistent database+original recovery sets,03:00 London,seven successful generations, failure visibility, isolated verified restore. This is a data-safety release gate. |
| Performance/final acceptance | Tickets26,29,30 not complete. Prior full local smoke passed254tests; not rerun for this planning audit. | Actual mini-PC latency measurement, phone/source/failure acceptance, release evidence and operating/recovery handoff. |

Primary evidence: individual tickets and their completion sections; `templates/base.html`, `templates/ledger/overview.html`, `ledger/admin.py`, `worker/client.py`, `compose.worker.yaml`, HLD sections5.3/10/11, and the current read-only host observations above. No private originals, credentials, model prompts or inference outputs were collected.

## 3. What went wrong in delivery management

1. Local ticket completion was communicated without a product-wide readiness view.254passing tests demonstrate covered behavior, not a finished product.
2. UI23 and advisory27 already had completed blockers; backup24 was also eligible apart from operational prerequisites. Host calibration18 should not have stopped those independent workstreams.
3. The ticket-plan summary still says20is in progress/21blocked, contradicting individual tickets. HLD open-work rows also mix already implemented code with actual remaining gates.
4. Setup scripts became the handoff focus before onboarding, visual acceptance, inference and recovery were complete.
5. The old release path permits excluding advisory inference. That must be reconciled explicitly with Sourav's current expectation rather than used to declare success prematurely.

## 4. Recommended ask-matt process

Use the existing repository and decisions; do not restart the entire wayfinding interview.

1. **grill-with-docs / grilling:** align on completion boundary, visual checkpoint and delivery authority using the questions below. Facts come from the repository/hosts, not repeated requests to Sourav.
2. **prototype:** after alignment, show a runnable disposable visual exploration for onboarding/dashboard/review, including empty, populated, uncertain and failure states. Approve the direction before building all screens. Synthetic data only; a prototype never counts as implemented delivery.
3. **to-spec:** amend the existing specification only for agreed changes, notably onboarding, inference release policy and LAN-only access. Keep accepted public test interfaces and financial semantics.
4. **to-tickets:** refine existing open tickets into demoable vertical slices and correct blocking edges. Publish revised tickets after approval, preserving completed ticket evidence. Do not create a duplicate30-ticket backlog.
5. **implement / implement-spec:** execute the approved dependency frontier, with one integration owner. Independent UI, inference and operations work may overlap only with stable contracts and separate edit ownership. Shared review/result models are coordinated, not concurrently rewritten.
6. **code-review + milestone demonstration:** review both standards and full ticket/spec compliance; show actual UI/runtime behavior and fix findings before marking acceptance complete.
7. **retro:** at milestones, update the progress/evidence process when it fails. Do not add tooling or rewrite architecture merely to improve process optics.

## 5. Proposed milestones and acceptance gates

These are planning checkpoints, not new tickets or permission to deploy. Existing approved tickets remain the implementation tracker until alignment.

### M0 — Rebaseline and agree what done means

- Reconcile source of truth: this plan, ticket summaries, actual installation report, remaining host gates, LAN-only access instead of stale VPN/TLS acceptance.
- Inventory deployed revisions/configuration without exposing secrets; inspect the existing laptop runtime/GPU and NAS destination using available access before asking for missing facts.
- Produce a release acceptance ledger: each applicable AC01–27 has owner, implementation status, local evidence, target evidence, unresolved issue and final disposition.
- Separate code prerequisites from target-qualification prerequisites. Propose splitting18's completed local recovery from its host calibration so19/22 can proceed against stable public contracts; preserve target qualification as mandatory for release. Do not silently bypass current edges.
- Exit: Sourav approves revised scope/process, with named blockers and no implied closure from installation.

### M1 — A usable web product, beginning with onboarding

Primary ticket23; extend/clarify first-run scope against01. Preserve12/13/14behavior.

Deliver in demoable slices:
1. Create/manage named accounts, sign in, see honest empty states, upload first original without using Django admin.
2. Desktop/mobile dashboard with clear spending/income/outgoing/net-cash hierarchy, period controls, evidence-aware history, currency/coverage/provisional distinctions and drill-down.
3. Upload/status and worker-unavailable/retry flows; searchable transactions and source evidence.
4. One-at-a-time review, correction history/revert, transfer/duplicate decisions; prepare space for model suggestions without fake results.

Exit: observed browser journeys with real application data, keyboard/focus/validation checks, narrow viewport and actual-phone smoke. No missing assets, dead controls or mock dashboard figures. Keep Django-rendered UI and small JS; no React rewrite. Reconcile SVG/Chart.js choice as a concrete presentation need, not an incidental migration.

### M2 — Complete and qualify laptop-local inference

Tickets27/28; runtime preparation and evaluation research can proceed while M1is built. Shared review presentation integrates after its contract is agreed.

- Decide runtime deployment from current host facts. Default proposal: project-managed Docker inference service with GPU access and pinned model/runtime, consistent with deployment policy; reuse native Ollama only through an explicit approved exception. Do not replace existing Ollama or disrupt other consumers.
- Confirm candidate documentation/license/structured-output support and choose at most two quantized candidates for the actual8GBGPU. Do not assume installed8Bmodel fits or is suitable.
- Implement one unresolved transaction→bounded local inference→validated suggestion→source-linked review→explicit user confirmation journey. Store model/prompt version, abstention and provenance separately from original facts and corrections.
- Test timeout, malformed/unsupported output and missing evidence; import still completes, manual review remains usable, advice retries are separate and bounded. No cloud fallback.
- Establish independent development/held-out labels before tuning. Gate:50held-out cases;>=90%correct non-abstained suggestions,>=50%coverage; compare rules-only baseline and report per-class failures.
- Measure100warm unresolved items within10minutes, cold load separately, memory and noOOM on the actual laptop. Verify worker-container-to-runtime connectivity and real inference, not just model listing/service uptime.
- Exit: selected pinned candidate passes and advice is demonstrated in the deployed UI; or explicit Sourav decision on a failed benchmark. Never automatically call the project complete with missing inference.

### M3 — Reliable processing and honest operations

Tickets18/19/20/21/22 and host acceptance in06; can overlap M1/M2where contracts permit.

- Finish result replay/stale fencing/concurrent correction and changed-identity recovery acceptance, reusing existing mechanisms.
- Calibrate claim heartbeat/expiry, retries and execution limits against actual parser/inference work. Verify no stale result can overwrite a newer result or confirmed correction.
- Exercise authorized real wake→readiness→claim→lease→result→release; failures/crashes leave bounded expiry, unrelated leases remain untouched. Test suspend/resume without forcing sleep on an in-use laptop.
- Verify restart/boot scheduling and missed-slot catch-up, no-wake-on-empty, and visible queued/unavailable states.
- Add operational status with last successes/actionable failures for processing, advice and backups; verify logs do not expose financial contents or credentials.
- Exit: repeatable controlled-failure scenarios preserve originals and committed figures, recover or report failure correctly, with actual-host evidence. No blanket timing assumption from Mac tests.

### M4 — Recoverable financial data

Tickets24/25; start design/implementation in parallel with M1, not after all styling/inference work. Actual deployment requires verified NAS destination and approval.

- Create consistent original+database+correction recovery sets, including imports/edits during backup; design the consistency boundary explicitly.
- Schedule03:00Europe/London; retain seven successful generations; interrupted/failed copies never retire good backups or authorize local deletion.
- Show last success and ongoing failures; NAS unavailable does not break normal application use.
- Restore into an isolated database/storage target and verify original bytes, evidence links, reports and corrections. Never test by overwriting the live database.
- Exit: successful backup plus measured isolated restore and NAS-failure exercise; documented recovery window and commands. No complete-release claim before this gate.

### M5 — Integrated release qualification and handoff

Tickets06/26/29/30, plus inference disposition27/28under the agreed completion boundary.

- Compare all four actual source families with independent private expected results; exercise overlap, repayments/transfers, refunds, excluded sections, savings gaps and correction/reprocessing scenarios.
- Confirm complete desktop/phone journeys and ordinary operation with laptop/NAS unavailable.
- Actual mini-PC:100,000transactions/up to10years,>=30warm repetitions per representative dashboard/period/search journey, p95<=2seconds, cold load reported separately.
- Verify deployment update/restart/recovery and safe rollback procedure, scoped credentials/private access, logs and repository privacy.
- Supply a release ledger linking each applicable acceptance criterion to observed evidence; every failed/unrun gate remains visible. Sourav accepts the demonstrated product.
- Exit: usable UI, actual qualified inference (or explicitly agreed disposition), financial correctness, recovery and performance accepted. Commit/release handoff does not authorize push automatically.

## 6. Ownership and reporting

- **Assistant, PM:** maintain capability/evidence ledger, dependency frontier, risks, decisions, milestones and next deliverable. Never stop the whole project at an unrelated blocked ticket.
- **Assistant, tech lead:** stable contracts, implementation design, deterministic-money invariants, TDD at approved interfaces, integration and independent review. Inspect available host/repo facts before requesting information.
- **Sourav:** completion-policy/visual choices, private oracle or independent-label judgement where required, actual-phone acceptance, live mutation/fault-test permissions and final product acceptance.
- Every milestone report: user-visible result; what was actually exercised locally/on host; unresolved risks; next ready work. Demonstrate the product, not just a test-count increase.
- Planning approval, task publication and visual approval do not authorize implementation. Begin only after Sourav explicitly authorizes implementation and its scope. Deployment, live data migrations, destructive operations and push remain separate approval gates.
- No artificial timeline estimates before runtime/model and host evidence establish the work. Sequence and exit criteria are the commitment.

## 7. Approved alignment and next checkpoint

Sourav accepted all three recommendations:

1. Full UI, qualified local advisory inference, recovery/backups and real-host acceptance define completion. A failed two-candidate evaluation requires an explicit decision, not silent scope reduction.
2. Present a runnable onboarding/dashboard/review visual prototype with populated, empty, uncertain and failure states before implementing the complete UI.
3. The assistant owns backlog execution, integration and milestone demonstrations. Live mutations and fault tests still require bounded explicit approval.

Visual choice: A's overview shell with side-by-side source/decision review. The assistant began real UI work prematurely; Sourav instructed it to stop and preserve that work. It is an unaccepted work-in-progress input to the tasks below, not a completed milestone. Next checkpoint: approve task granularity and dependencies, then publish individual tickets. Do not execute them without separate authorization.

## 8. Proposed implementation tasks — awaiting planning approval

These are draft task IDs, not newly published tickets or ready-to-execute claims.
They refine existing tickets rather than replacing completed work or duplicating
the backlog. On approval, publish each agreed slice separately, retaining links
to the existing acceptance criteria and historical evidence. No parent ticket is
closed by this proposal. “None” below means no remaining technical dependency,
not permission to implement.

All tasks include applicable public-interface behavioral tests, integration,
standards/spec review and an observable demonstration. Local evidence and
actual-host acceptance are recorded separately. Existing partial implementation
must be reviewed and reused where sound, not automatically accepted or rebuilt.

### T01 — First-use account and upload journey
Existing scope: 01/02/03/23. Blocked by: None.
- Sign in, create a named account, upload its first supported statement and reopen
  the preserved original without Django admin; validation and rejection are clear.
- Duplicate/invalid account submissions cannot corrupt existing accounts; last
  account selection and consolidated savings mapping remain usable.
- Audit and finish the preserved onboarding/UI work; demonstrate empty and
  successful journeys against real local PostgreSQL and isolated files.
- Excludes account deletion/type changes; any broader account-management need
  requires explicit scope agreement.

### T02 — Evidence-first dashboard and transaction navigation
Existing scope: 12/13/23. Blocked by: None.
- Approved A layout, real period-selected metrics, dated balances/history,
  provisional/disputed/unknown states and honest coverage gaps.
- Metric and original-description search lead to supporting transactions and
  originals; period context and pagination survive navigation.
- Demonstrate populated and empty states on desktop and narrow viewports.
  Reuse existing financial semantics and SVG evidence chart; no chart-library
  migration unless a concrete requirement justifies it.

### T03 — Source-first review and reversible decisions
Existing scope: 14/15/16/17/23. Blocked by: None.
- Side-by-side source and decision on desktop; source accessible before actions
  on narrow screens. Reach review from transaction/search/metric journeys.
- Confirm/revert classification, inspect history, resolve duplicate/transfer/
  repayment/reversal candidates without rewriting source facts.
- Demonstrate changed reporting effect and restored effect after revert, plus
  rejected invalid decisions and preserved history.

### T04 — Understand and recover an upload's processing state
Existing scope: 18/20/23. Blocked by: None.
- Receipt distinguishes preserved, queued, processing, imported, partial,
  unsupported and failed states; shows actionable next steps and original access.
- Process now and bounded retry reach real worker outcomes; worker unavailable
  does not prevent ordinary browsing or accepted-original access.
- Exercise real local worker/API round trips and failure states; actual wake and
  target timing qualification belong to T10.

### T05 — Isolated laptop inference runtime and worker connectivity
Existing scope: 27/28 and runtime prerequisite. Blocked by: None.
- Implement the agreed project runtime deployment, pinned model/runtime and
  worker-container connectivity; demonstrate a real local structured response.
- No production suggestions enabled, no cloud fallback, no interference with
  existing Ollama consumers; record cold load and memory observations.
- Before implementation: resolve Docker runtime versus explicitly approved
  native-service reuse, candidate/license suitability and resource limits.
  Any installation/download/service changes require bounded host approval.

### T06 — One validated suggestion through explicit user confirmation
Existing scope: 27. Blocked by: T05.
- Unresolved transaction → bounded local inference → validated source-linked
  classification or abstention → review → explicit confirmation or dismissal.
- Preserve model/prompt version and provenance; suggestions cannot rewrite
  amounts, dates, balances or override confirmed corrections.
- Demonstrate the whole path in isolation. T08 gates normal-use enablement,
  not controlled evaluation; this avoids a qualification/implementation cycle.
- Integrate with T03 through the existing review interface; shared ownership
  must be coordinated, but visual polish is not a technical blocker.

### T07 — Advisory failure and separate bounded recovery
Existing scope: 27. Blocked by: T06.
- Timeout, missing runtime, malformed output or unsupported source evidence
  leaves deterministic imports and manual review usable.
- Advice retry is bounded and independent of financial reimport; obsolete
  suggestions cannot replace confirmed corrections.
- Show failure, retry and abstention honestly without private content in logs.

### T08 — Qualify the model and gate enablement
Existing scope: 28. Blocked by: T05, T06, T07.
- Establish independent development/held-out labels before tuning; evaluate at
  most two candidates and compare with the rules-only baseline.
- At least 50 held-out cases; at least 90% correctness among non-abstained
  suggestions and at least 50% coverage; report per-class failures.
- Actual laptop: 100 warm unresolved items within 10 minutes, cold load
  separately, memory recorded and no OOM; enable only a pinned passing candidate.
- Both fail → keep advice disabled and return to Sourav for an explicit decision.
  This is not permission to declare deterministic-only completion.

### T09 — Preserve financial results and corrections across interruptions
Existing scope: local portion of 18 plus 19. Blocked by: None.
- Verify/fill gaps in bounded lease recovery, lost-ack replay, conflicting
  payloads, stale attempts, concurrent corrections and changed-identity reprocessing.
- Interrupted or repeated work cannot duplicate financial effects or replace
  newer results/user corrections; source/history remains available.
- Use real PostgreSQL/files and approved controlled interfaces. Propose removing
  host-calibration as a blocker of local 19 work; retain it as mandatory T10
  acceptance. This dependency adjustment needs planning approval.

### T10 — Qualify real-host scheduling, wake and keep-awake lifecycle
Existing scope: 06/18/20/21. Blocked by: T09; T08 for final combined parser/inference timing.
- Verify LAN deployment baseline, nightly scheduling/restart catch-up, Process
  now, no wake for empty work and real worker-readiness transitions.
- Demonstrate wake → claim → bounded owned lease → result → release, expiry,
  failures and suspend/resume without touching unrelated leases/services.
- Calibrate timings against qualified workloads. Parser/controller checks can
  start earlier; final combined acceptance waits for T08.
- Requires approved host deployment, power/fault scenarios and safe timing window.

### T11 — Actionable operational status without private logging
Existing scope: 22. Blocked by: T04, T07, T09, T12.
- Surface processing/advice/backup last success and unresolved failure with next
  action, distinguishing running services from functional readiness.
- Normal use remains independent of laptop/NAS availability; diagnostics contain
  neither original financial contents nor credentials.
- Each producer task exposes its own honest status; this task integrates those
  statuses, not a generic telemetry platform.

### T12 — Consistent scheduled backup with safe retention
Existing scope: 24. Blocked by: None.
- Consistent database + originals + corrections recovery generation while
  imports/edits continue; define the committed-state boundary before coding.
- Run at 03:00 Europe/London; keep seven successful generations; retire an old
  generation only after a new complete success.
- Interrupted/full/unavailable NAS and schedule/DST/catch-up failures are visible;
  no local deletion and no disruption of normal application use.
- Prove locally, then on approved NAS destination. Resolve path/headroom,
  consistency protocol and target permissions before the relevant implementation.

### T13 — Restore and verify a recovery generation in isolation
Existing scope: 25. Blocked by: T12.
- Restore into a separate database/storage target; verify original bytes,
  evidence navigation, reports, mappings and confirmed corrections.
- Reject incomplete/unusable generations and report measured recovery steps
  and recovery-window limits; never overwrite the live database for a test.
- Requires approval for actual NAS/host restore exercise and isolated capacity.

### T14 — Verify actual supplied statement families end to end
Existing scope: 06/07–10/15–17/29. Blocked by: T09.
- Compare Lloyds Current/Credit, Amex and included Revolut GBP/savings against
  independently established expected results, using private files outside Git.
- Include overlap, repayments, transfers, cash/refunds, excluded sections,
  missing savings coverage, mismatch and partial-section outcomes.
- Existing parsers are not rebuilt. Record exact supported-format limits and
  fix proven discrepancies only within approved implementation scope.

### T15 — Measure and meet real-host dashboard/search latency
Existing scope: 26. Blocked by: T02.
- On an approved isolated mini-PC deployment, use 100,000 synthetic transactions
  spanning up to ten years; at least 30 warm repetitions per representative
  dashboard/period/search journey, p95 at most two seconds.
- Report cold first load, dataset/query/browser/network/runtime conditions;
  optimize and repeat only where needed. Never seed benchmark data into live DB.
- Requires an actual-host deployment baseline and resource approval; does not
  wait for unrelated wake/backup work.

### T16 — Accept complete desktop, keyboard and actual-phone journeys
Existing scope: 23/29. Blocked by: T01, T02, T03, T04, T07, T08, T11.
- Exercise onboarding, upload, dashboard, search, original access, corrections,
  qualified advice and failure/status journeys in the integrated application.
- Check labels, focus, errors, control targets and narrow layouts; include an
  actual phone, not only browser viewport emulation.
- Requires approved deployment and Sourav's actual-device acceptance; earlier
  local browser checks remain evidence, not a substitute.

### T17 — Integrated release qualification and operating handoff
Existing scope: 29/30. Blocked by: T10, T13, T14, T15, T16.
- Map every applicable AC-01–27 to observed local and real-host evidence;
  no unrun/failed criterion silently disappears.
- Verify ordinary use without laptop/NAS, approved update/restart/rollback,
  runtime configuration, privacy and recovery procedure.
- Deliver reviewable release evidence and operating instructions for Sourav's
  acceptance. Final release/deployment and push still require explicit approval.

## 9. Planning decisions before task publication

1. Approve or revise these end-to-end slices and genuine blocking edges.
2. Approve splitting local recovery implementation from real-host calibration,
   without removing either acceptance requirement.
3. Confirm that first-use account management means create/list/select only;
   rename/type-change/delete are not silently included.
4. Resolve runtime reuse/deployment, inference contract/labels and backup
   consistency/target decisions in focused planning follow-ups using repo/host
   evidence first. Unresolved decisions remain explicit gates, not agent guesses.
5. Publish approved individual task files linked to existing tickets. This
   completes task planning only; implementation remains paused until explicitly
   authorized by Sourav.
