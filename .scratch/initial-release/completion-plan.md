# Product completion plan

Status: direction approved by Sourav (“Yes to all”): complete product including qualified inference; visual prototype before full UI implementation; assistant-owned milestone execution. Live deployment, data migrations, destructive operations and pushes retain explicit approval gates.
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
- Implementation may progress autonomously within the approved plan. Preserve existing explicit approval for deployment, live data migrations, destructive operations and push; group planned host acceptance into bounded requests rather than repeated ad-hoc permission prompts.
- No artificial timeline estimates before runtime/model and host evidence establish the work. Sequence and exit criteria are the commitment.

## 7. Approved alignment and next checkpoint

Sourav accepted all three recommendations:

1. Full UI, qualified local advisory inference, recovery/backups and real-host acceptance define completion. A failed two-candidate evaluation requires an explicit decision, not silent scope reduction.
2. Present a runnable onboarding/dashboard/review visual prototype with populated, empty, uncertain and failure states before implementing the complete UI.
3. The assistant owns backlog execution, integration and milestone demonstrations. Live mutations and fault tests still require bounded explicit approval.

Next checkpoint: compare three structurally different visual directions on a synthetic-only, isolated prototype. Record the chosen direction before production UI work. The prototype is not an installed feature or evidence of functioning inference/backup.
