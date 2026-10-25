# First release: personal statement import and financial dashboard

Authority: retained requirements and acceptance baseline, not an execution queue.
Release: R1
Design baseline: decisions accepted through Q76
Implementation direction: the [product-completion backlog](../product-completion/ticket-plan.md) and its [completion specification](../product-completion/spec.md) exclusively govern remaining work, authorization and release gates. Earlier plans/tickets are historical evidence. Qualified local inference remains required unless Sourav explicitly revises scope. Implementation is paused pending explicit authorization.

## Problem Statement

Sourav's bank and credit-card statements contain the evidence needed to understand
spending and cash, but their layouts, date ranges and transaction meanings differ.
Adding statement totals double counts card repayments and own-account transfers.
Incomplete history, duplicate imports and ambiguous descriptions can make an
apparently precise dashboard misleading. Financial data must stay on Sourav's
machines and remain usable while the processing laptop sleeps or NAS backups
are unavailable.

## Solution

Provide a private, single-user web application that preserves manually uploaded
originals, extracts financial facts deterministically, and presents spending,
income, cash outgoing and net cash history with source evidence and visible
uncertainty. Sourav can investigate figures, correct records and confirm ambiguous
matches on desktop or phone. Optional local-model classification advice assists
review without changing financial facts or bypassing confirmation.

The mini-PC owns authoritative state and ordinary application use. A laptop
processes eligible uploads in batches through the application's interface. NAS
stores consistent backup generations, outside the live data path. This release
supports the four supplied statement families, not arbitrary bank documents.

### Supported source and account scope

| Statement family | Included activity | Important limitation |
| --- | --- | --- |
| Lloyds Current | Current account transactions and supplied balances | Accessibility text must not corrupt visible table extraction. |
| Lloyds Credit | GBP billed transactions, credits, standalone fees and supplied debt balances | Transaction date and date entered differ; statement date does not imply calendar-month coverage. |
| Amex Credit | GBP billed transactions, credits and supplied debt balances | Process date differs from purchase date; annual summaries and embedded FX disclosures must not become extra transactions. |
| Revolut consolidated | Personal GBP and savings GBP as separate named accounts | Ignore joint accounts, non-GBP accounts and crypto sections. Savings transaction evidence lists interest receipts only. |

One combined Revolut original can support both included named accounts. Confirm
its section-to-account mapping on first import and reuse it only while source
identities remain consistent. Excluding a section does not remove it from the
preserved original or require manual PDF splitting.

The four supplied PDFs establish representative layouts. Supported text/CSV
exports require explicit format contracts and fixtures before enabling their
extraction; accepting an unknown readable layout does not establish support.
Neither the input filenames nor the supplied card cycles establish complete
August coverage.

## User Stories

1. As Sourav, I want private authenticated access. For the first deployment I have selected trusted-LAN direct HTTP with Pi-hole DNS and no reverse proxy; private HTTPS/VPN remains later work before broadening access.
2. As Sourav, I want one personal login, so that I can use the app without managing additional users.
3. As Sourav, I want named accounts, so that bank activity and credit-card debt remain distinguishable.
4. As Sourav, I want to upload supported statement files manually, so that I control what enters the app.
5. As Sourav, I want the last account selection remembered, so that repeated uploads are convenient.
6. As Sourav, I want detectable source/account mismatches flagged, so that activity is not silently assigned elsewhere.
7. As Sourav, I want one Revolut upload mapped to personal GBP and savings GBP, so that I do not split its PDF.
8. As Sourav, I want excluded Revolut sections ignored, so that joint accounts, other currencies and crypto do not complicate this release.
9. As Sourav, I want clear rejection reasons, so that I know when a file cannot be safely accepted.
10. As Sourav, I want readable unsupported originals preserved with a visible issue, so that extraction failures do not lose evidence.
11. As Sourav, I want acceptance only after local preservation succeeds, so that successful upload means the original and its tracking record survive restart.
12. As Sourav, I want to open original evidence from a transaction, so that I can verify extracted facts.
13. As Sourav, I want transaction and posting dates retained separately, so that reporting dates remain explainable.
14. As Sourav, I want amounts and credits normalized exactly, so that totals do not depend on model guesses or floating-point approximations.
15. As Sourav, I want repeated uploads and retries to avoid duplicate financial effects, so that reprocessing is safe.
16. As Sourav, I want identical-looking genuine purchases preserved, so that conservative duplicate detection does not delete spending.
17. As Sourav, I want transfers and card repayments linked without merging their entries, so that both accounts remain traceable.
18. As Sourav, I want ambiguous matches sent to review, so that uncertainty is not hidden in totals.
19. As Sourav, I want pending uploads processed at 21:00 Europe/London, so that laptop work is batched.
20. As Sourav, I want Process now to release waiting uploads, so that I can request processing without waiting for tonight.
21. As Sourav, I want repeated Process now clicks to be safe, so that they do not duplicate or interrupt work.
22. As Sourav, I want visible wake/readiness and failure states, so that I know why processing is delayed.
23. As Sourav, I want active processing to keep the laptop awake temporarily, so that work can finish without taking over normal sleep policy.
24. As Sourav, I want failed jobs to retain originals and committed data, so that retry does not damage usable records.
25. As Sourav, I want the dashboard to default to twelve months with selectable periods, so that I can understand both recent and historical activity.
26. As Sourav, I want spending, income and cash outgoing shown separately, so that card purchases and repayments are not added twice.
27. As Sourav, I want net cash to include tracked savings and subtract card debt, so that the graph reflects the agreed account scope.
28. As Sourav, I want dated balances and visible coverage gaps, so that sparse history does not appear complete.
29. As Sourav, I want to open the transactions behind a metric, so that I can explain its total.
30. As Sourav, I want simple original-description search, so that I can find activity without conversational search.
31. As Sourav, I want GBP converted into foreign currency counted as spending, so that excluded foreign accounts need no ledger.
32. As Sourav, I want conversions back into GBP to reduce spending, so that returned funds are not mistaken for earned income.
33. As Sourav, I want savings interest recorded without invented principal movements, so that limited exports remain useful and honest.
34. As Sourav, I want cash withdrawals and evidenced reversals handled consistently, so that classifications match the agreed reporting rules.
35. As Sourav, I want one review issue with its source and proposed effect visible, so that I can confirm or reject a change deliberately.
36. As Sourav, I want corrections retained across reprocessing and reversible with history, so that machine results cannot silently erase my decisions.
37. As Sourav, I want core upload, dashboard, search and review flows on my phone, so that I do not need a desktop to use the app.
38. As Sourav, I want optional local-model suggestions for unresolved classifications, so that review requires less interpretation work.
39. As Sourav, I want validated facts available even when advice fails, so that model availability cannot block the core application.
40. As Sourav, I want normal use without the laptop or NAS, so that compute and backup outages do not make committed data inaccessible.
41. As Sourav, I want seven successful nightly backups and visible failures, so that recovery has a clear, bounded history.
42. As Sourav, I want an isolated restore verified, so that a backup is more than a successful file copy.
43. As Sourav, I want local history retained, so that twelve months is a viewing default rather than a deletion policy.
44. As Sourav, I want project services to recover after restart, so that routine crashes or reboots do not require rebuilding state.
45. As Sourav, I want processing/backup failures and last-success times visible, so that I can notice problems when opening the app.
46. As Sourav, I want operational logs to omit private financial contents and credentials, so that diagnosis does not create another sensitive dataset.

## Implementation Decisions

### Ownership, deployment and modules

- Use a Django application with custom responsive rendered pages, small JavaScript
  modules and Chart.js; use a Python laptop worker. No separate React application
  or queue/search service is required.
- Deploy project application, worker and dedicated PostgreSQL in Docker. Native
  project deployment requires an explicitly discussed, very simple exception.
  Existing vendor databases and native infrastructure are separate and untouched.
- Store PostgreSQL data, accepted originals and historical authoritative records
  on mini-PC local persistent storage. NAS is backup storage, not project compute,
  live database storage or an outage fallback authority.
- Keep clear internal responsibilities for intake/preservation, format-specific
  interpretation, matching/reporting, job coordination/publication, review,
  advisory interpretation and recovery operations. These are module
  responsibilities, not instructions to add separate deployable services.
- Develop on the Mac with as much appropriate local testing as possible. Actual
  deployment-host E2E checks occur at meaningful milestones. Sourav selected
  Docker Desktop as the Mac test runtime for isolated PostgreSQL and files; it
  is installed and verified with pinned dependencies.

### Intake, financial evidence and matching

- Cap each file at 20 MiB and PDFs at 100 pages. Reject unreadable/corrupt,
  password-protected and image-only inputs with a clear reason. No OCR/password
  workflow. Check actual content, not only its extension.
- Preserve readable accepted originals with unsupported extraction as explicit
  issues; never describe them as successfully imported transactions.
- Acceptance requires the original and tracking record durably preserved locally.
  Local storage failure cannot yield false success. NAS unavailability does not
  block intake. Design and test recovery across interrupted file/record updates.
- Preserve source entries independently of logical transactions, with upload,
  account section and page/row/text-region evidence where available. Preserve
  source amount, sign/CR marker, currency, description and date meanings.
- Normalize GBP ledger values to integer pence. Do not silently round malformed
  values or use binary floating point for financial calculations. Original FX
  details are annotations, not additional billed transactions.
- Report by posting/booking date: Lloyds Credit date entered and Amex process
  date where supplied. Retain purchase date separately. Infer missing years only
  from defensible statement context; ambiguous year boundaries require review.
- Validate source-supported running balances, totals and opening/closing equations.
  Do not turn summaries, payment due dates, annual totals or embedded FX fee
  disclosures into extra executed transactions.
- Repeated identical originals under the same confirmed mapping have one set of
  financial effects. Different originals may support the same transaction only
  when reliable account-specific evidence establishes overlap. Matching
  date/amount/description alone cannot silently merge distinct payments.
- Own-account transfers and repayments link distinct account transactions; they
  are not duplicate merges. Equal/opposite amounts and nearby dates alone do not
  prove a pairing or ownership. Uncertain matches remain reviewable. Automated
  evidence rules require fixtures before enabling them; no heuristic time window
  is approved merely by this specification.

### Reporting and review

| Event | Spending | Income | Cash outgoing / net cash |
| --- | --- | --- | --- |
| Purchase, separately charged fee or interest charged | Increase at posting | No | Debit/current outgoing when posted there; credit purchases increase card debt. |
| Refund, explicit fee waiver or evidenced returned payment | Reverse its original classification in the posting period | Not automatically income | Preserve the posted cash movement; incoming reversals do not net down gross outgoing. |
| Salary or received interest | No | Increase when identified | Preserve the corresponding account movement/balance. |
| Linked current-to-card repayment | No additional spending | No | Include current-account outgoing; card credit reduces debt. |
| Other linked transfer between tracked own accounts | No | No | Exclude from external cash outgoing; combined net cash unchanged when both sides are evidenced. |
| Cash withdrawal | Increase | No | Include outgoing at posting; no cash-wallet ledger. |
| Revolut GBP converted into foreign currency | Increase | No | Include GBP outgoing; ignore the foreign leg and later foreign purchases. |
| Foreign currency converted back into Revolut GBP | Reduce in its posting period | No | Record GBP incoming; do not import the foreign leg. |
| GBP movement involving an excluded joint/crypto/investment account | Review if unclear | Review if unclear | Retain GBP-side movement and balance effect without importing the excluded account. |

- Net cash is tracked current/debit plus savings balances minus outstanding card
  debt. Keep currencies separate; do not introduce an FX-consolidated portfolio.
  Revolut scope is personal GBP and savings GBP only.
- Savings balance observations contribute to net cash and explicit interest to
  income. An interest-only export does not establish principal movements or a
  complete daily history; flag unexplained balance changes without inventing rows.
- Exclude unresolved monetary facts from affected totals. Uncertain classification
  or matching makes affected totals provisional. Coverage gaps and pending work
  remain visible; an excluded product is not a missing tracked-account section.
- Keep the twelve-month default with month/year/custom selection. One selected
  period controls metrics and graph. Clicking a metric opens its supporting
  transaction list with period context and explainable inclusions/exclusions.
- Show account-level dated balances/debt and links to coverage/review issues.
  Do not draw unsupported graph gaps as verified daily history; sparse evidence
  can appear as dated points. Search matches original names/descriptions.
- Review one issue with source evidence, extracted values, proposed change/match
  and before/after effect. Require explicit save/confirm/reject. Reverting a user
  correction restores the source-derived value through validation while retaining
  history. No bulk approval. Support these core flows on phone and desktop.
- Keep machine-derived values separate from user corrections. Preserve concurrent
  confirmed edits and flag contradictions. If changed transaction identity cannot
  safely retain a correction, keep the prior view and request review.

### Worker and publication contracts

- One upload is one job; run one active worker job initially. Download only assigned
  originals and submit structured results through authenticated application
  interfaces; no shared original mounts or worker database credentials. Clean
  temporary laptop files on completion and after crashes.
- Publish a validated upload result as one consistent update, including status
  and issues. A failed account section contributes no new financial facts and
  retains its prior view. Independently valid sections may publish with a visible
  partial outcome. Ignored sections do not cause reconciliation failure.
- An attempt holds a renewable job claim. Missed heartbeats permit expiry/retry;
  the worker stops when it detects lost ownership. Expired/stale attempts cannot
  replace newer results. Computation may repeat; financial effects must not.
- A stable attempt identity makes identical resubmission return recorded success
  after a lost acknowledgement, without applying effects twice. Reject conflicting
  content under the same identity. Validate before committing/publication.
- Core transient processing failures get at most three total attempts with
  increasing delays, then visible failure/manual retry. Repeatable format or
  validation failures go to review. Wake checks do not consume those attempts.
  Optional advice failure follows the separate degradation rule below.
- A failed upload does not block other eligible uploads. Serve the last committed
  data throughout processing and reprocessing; expose no uncommitted result as
  completed. Corrections remain authoritative across every retry/publication path.

### Scheduling, laptop power and visibility

- Release pending uploads daily at 21:00 Europe/London. An already-awake laptop
  does not itself make pending work eligible. With no due work, do not wake it.
- Process now releases all currently waiting uploads and requests wake if needed;
  repeated clicks neither duplicate work nor interrupt an active job. Show
  asynchronous queued/waking/processing/unavailable/failure status.
- Allow ten minutes from wake request to application-worker readiness, then show
  unavailable and retain queued work for manual retry or next batch. Do not
  continuously send wake requests. A wake acknowledgement or cached controller
  health is not application-worker readiness or GPU readiness.
- Use existing controller create/extend/release actions for bounded active-work
  keep-awake leases. Renew only while legitimately processing and release only
  the application's own lease on completion. Crashes leave bounded expiry. Do
  not release user leases or force laptop sleep.
- Keep job ownership claims separate from sleep-inhibition leases. Controller
  extension is additive and capped at eight hours from lease creation; the
  adapter must handle that ceiling without blindly accumulating long inhibition.
- After mini-PC downtime, perform one catch-up per missed schedule rather than
  replaying every missed day. Test timezone/DST and restart behavior explicitly.
- Restart project containers after crash/reboot with safe work recovery. Upgrades,
  migrations and restores are deliberate operations, with approval when affecting
  existing data. Deployment approval and Git push approval remain separate.
- Show unresolved failures and last successful processing/backup times in-app.
  No external notifications initially; Sourav must open the app to notice them.
  Logs contain job IDs, stages, timings and sanitized errors, excluding statement
  contents, transaction descriptions, account identifiers and credentials.

### Authentication and privacy

- Use one Sourav login through Django authentication, without public exposure or
  self-service registration. Sourav explicitly selected LAN-only direct HTTP for
  initial setup; it does not encrypt credentials, tokens or statements. Private
  HTTPS/VPN and certificates are deferred, not provided by DNS.
- Give the worker a separate replaceable credential scoped to claims, assigned
  original downloads, progress and result submission. It grants neither user
  login rights nor direct database access. Protect original/evidence access.
- Keep real statements, credentials and unredacted financial fixtures outside
  Git. No cloud AI or remote document/model processing. Exact private routing,
  certificate provisioning and controller machine authentication require verified
  integration, not assumptions from existing installed infrastructure.

### Backups, retention and recovery

- Retain imported history and active originals locally. Twelve months is a view
  default, not a purge policy. Automatic archival of old originals is deferred.
- At 03:00 Europe/London create a consistent recovery set of originals and
  authoritative records/corrections on NAS. Processing need not finish first;
  backup must represent consistent committed state and associated originals.
- Keep seven successful generations; incomplete copies are not successful.
  Retire the oldest only after a new generation completes. Show last success
  and failures. NAS outage does not stop ordinary use or authorize local deletion.
- Verify restoration in an isolated target, including evidence and corrections.
  Sourav accepts loss since the last successful backup; failed runs extend that
  window. NAS backups do not remove whole-site or NAS power-loss risk. Container
  restart cannot repair arbitrary persistent corruption. Verify local storage
  behavior without claiming restart tests prove physical power-loss durability.

### Optional local interpretation

- Suggest only unresolved financial classifications: spending, income, transfer,
  refund or unknown. Use extracted facts and bounded relevant context. Validate
  allowed structured values, source references and a brief explanation; permit
  abstention. User confirmation is required before financial classification effects.
- Do not use the model to parse/repair amounts, dates or balances, to invent
  transactions, or to override deterministic facts and confirmed corrections.
- Optional model failure does not fail or repeat a validated financial import.
  Publish validated facts with unresolved review/advice-unavailable status; bound
  separate advice retries. Core job failures retain their three-attempt policy.
- Before enabling advice, evaluate at most two documented local quantized
  candidates on the actual laptop. Exact model/runtime is unselected. Existing
  native Ollama is not permission to bypass the project Docker constraint.
- Require at least 90% correct non-abstained suggestions and at least 50% coverage
  on 50 independently labelled held-out cases, including legitimate unknowns.
  Report counts and per-class failures; do not tune on the hold-out or count
  abstention as an answered suggestion. This pilot does not prove general reliability.
- Target 100 unresolved items in ten minutes of warm inference, recording cold
  load separately, with stable operation on the laptop's existing 8 GB GPU and
  no out-of-memory failures. These are acceptance targets, not observed results.
- If neither candidate passes, keep advice disabled for safety and bring the
  benchmark evidence to Sourav for an explicit scope decision. Under the approved
  completion plan, a deterministic-only application is not automatically a
  completed release. No cloud fallback; retain actual benchmark evidence.

## Testing Decisions

Test externally observable behavior through the following user-approved seams.
Expected values come from independently reviewed examples/source facts, not the
implementation under test. Work one failing behavioral test and minimum working
slice at a time; review before completion. Avoid private-method tests, internal
mock choreography and database side-channel assertions.

| Public test interface | What it catches | What it does not establish |
| --- | --- | --- |
| Statement interpretation and reporting | Supported layout/date/sign extraction, arithmetic, validation and reporting rules | Persistence transactions, browser wiring or host behavior. |
| Application upload/job/result/review/report interfaces with real PostgreSQL and isolated files | Preservation, authorization, claims, idempotency, section publication and correction precedence | Browser rendering or physical GPU/controller behavior. |
| Browser journeys | Login, upload/status, metric/source drill-down, search and review in desktop/narrow layouts | Physical phone behavior or actual faults unless exercised there. |
| Infrastructure adapters and operational commands | Controlled failure behavior plus actual-host wake/leases, restart, backup and restore | Fakes cannot prove physical behavior; restart does not prove power-loss durability. |

No existing application or test suite provides prior art. The supplied-format
inspection and invented import examples are evidence/expected-outcome inputs,
not production parser code or completed tests. Use controllable clocks/external
adapters for local fault scenarios, but exercise actual database/file behavior.
Docker Desktop is the selected Mac runtime; install and verify it before
PostgreSQL-dependent tests.

### Required fixtures and release evidence

- Synthetic/sanitized fixtures for each supported layout, including accessibility
  text, multiline descriptions/CR, distinct date meanings, year boundaries, FX
  annotations/fee differences, multiple account sections and repeated headers.
- Independent expected transactions, balances and reporting effects for duplicate
  files, overlaps, identical-looking distinct purchases, repayments, transfers,
  refunds, cash, savings incompleteness and excluded Revolut sections.
- Invalid/oversize/password/image-only inputs; unsupported readable formats;
  lost acknowledgements, stale claims, crash cleanup, concurrent corrections,
  partial publication, optional advice failure and interrupted backup/restart.
- Verify all four actual source families using external private originals for
  release. The supplied card cycles do not establish a full-August oracle;
  adjacent sources may be required to verify additional coverage/overlap cases.
- Separate model-development and held-out evaluation cases from parser fixtures.
  Preserve independent labels before inference. Do not claim memory fit or
  inference quality from source inspection or a stubbed model.

### Acceptance matrix

Every row is required for the relevant release capability. No row is passed yet.
The model row gates enabling advice; disabling advice does not waive core gates.

| ID | Observable acceptance | HLD trace |
| --- | --- | --- |
| AC-01 | Private login works over home/VPN routes; unauthenticated requests cannot obtain originals, evidence or protected operations; worker credentials cannot exercise user/DB privileges. | FR-SEC-01; NFR-PRI-01 |
| AC-02 | Supported uploads associate with confirmed named accounts; last selection is remembered, identity mismatches are visible, Revolut maps both included accounts without splitting. | FR-ING-01; FR-ING-02 |
| AC-03 | Invalid/password/image-only and limit-exceeding inputs get clear rejection; readable unsupported originals remain preserved with explicit unsupported status. | FR-ING-01 |
| AC-04 | A successful receipt survives service restart with original/tracking evidence; storage failures never report success. | FR-ING-03; NFR-DUR-01 |
| AC-05 | Each supported family agrees with independent expected dates, signs, amounts, balances and provenance; summaries/FX annotations are not extra transactions. | FR-PRO-01; NFR-EXP-01 |
| AC-06 | Repeated files, lost acknowledgements and retries have one set of financial effects; conflicting attempt payloads are rejected. | FR-PRO-03; NFR-INT-01 |
| AC-07 | Overlap preserves evidence; distinct identical-looking purchases remain separate without stronger evidence; ambiguous candidates require review. | FR-MAT-01; NFR-INT-01 |
| AC-08 | Linked transfers/repayments retain both entries and agreed reporting effects, including current-account repayment outgoing without double spending. | FR-MAT-02; FR-DASH-01 |
| AC-09 | Refunds, fee waivers, returned payments and cash withdrawals produce the agreed posting-period effects; incoming is not automatically income. | FR-DASH-01 |
| AC-10 | Revolut imports personal/savings GBP only; conversions out increase spending, returns reduce it, and excluded-account GBP movements remain traceable/reviewable. | FR-PRO-01; FR-DASH-01; FR-DASH-02 |
| AC-11 | Period-selected metrics, account balances and net cash follow known evidence; missing/sparse history and unresolved monetary/classification issues are visible. | FR-DASH-01; FR-DASH-02; NFR-EXP-01 |
| AC-12 | Description search and metric drill-down retain period context and reach supporting originals; core flows work on desktop and an actual phone. | FR-RET-01; FR-DASH-01 |
| AC-13 | Explicit correction/match review retains history; confirmed concurrent edits survive reprocessing; unsafe identity mapping preserves the previous view. | FR-REV-01; NFR-INT-01 |
| AC-14 | At 21:00 or Process now, due work releases without waking for an empty queue; already-awake alone does not process pending work; repeated clicks do not interrupt/duplicate. | FR-CTL-01; FR-CTL-02 |
| AC-15 | Worker obtains assigned originals and publishes through scoped application interfaces, never direct DB access; temporary files are cleaned after completion/crash. | FR-CTL-03; NFR-PRI-01 |
| AC-16 | Expired claims/stale attempts, three-attempt core retry policy, deterministic review failures and interrupted work behave as specified without corrupting committed data. | FR-CTL-02; FR-PRO-03; NFR-INT-01 |
| AC-17 | A failed section retains its previous view; valid sections publish consistently with partial status; no guessed reconciliation or partially committed completed result. | FR-PRO-03; FR-DASH-02 |
| AC-18 | Actual wake/readiness deadline and lease creation/renewal/release/expiry work, including the eight-hour ceiling and failure paths; unrelated leases remain intact and sleep is not forced. | FR-CTL-02 |
| AC-19 | Normal intake/dashboard/search/review/original access work while laptop and NAS are unavailable; NAS backup failure is visible. | FR-ING-03; NFR-AVL-01 |
| AC-20 | Project restart and one-run schedule catch-up recover work; timezone/DST and status visibility are verified without replaying every missed day. | FR-CTL-01; NFR-INT-01 |
| AC-21 | Backups at 03:00 succeed independently of processing; partial copies are not successful, seven successful generations remain, and failure cannot retire good recovery sets or delete local data. | FR-OPS-01; NFR-OPS-01; NFR-OPS-02 |
| AC-22 | Isolated restore recovers originals, authoritative records, corrections and evidence links; recovery loss window and any limitations are recorded. | FR-OPS-01; NFR-OPS-01; NFR-OPS-02 |
| AC-23 | Last-success/failure information is visible; logs and repository contain no real financial contents, account identifiers or credentials. | NFR-EXP-01; NFR-PRI-01 |
| AC-24 | Imported history older than twelve months remains available; no automatic purge/old-original archival occurs. | NFR-DUR-01; NFR-EXP-01 |
| AC-25 | Model output is advisory and validated; facts/confirmed values cannot be overwritten; unavailable advice leaves deterministic import and manual review usable. | FR-PRO-02; FR-PRO-03 |
| AC-26 | Before advice is enabled, the separate two-candidate actual-laptop evaluation passes correctness, coverage, time and memory gates with recorded limitations. | FR-PRO-02; NFR-PER-01 |
| AC-27 | Actual mini-PC home-LAN dashboard/period-update and text-search meet p95 at most two seconds under the measurement conditions below. | NFR-PER-01 |

### Performance and release gates

Measure 100,000 transactions over up to ten years, with one active user. Use at
least 30 timed repetitions per representative dashboard/period-update and simple
text-search journey after warm-up; measure submission to a usable visible result.
Record dataset/seed, query/range, browser, network, host/runtime and timing method.
Report cold first load separately. The p95 gate is two seconds on the actual
mini-PC over home LAN; Mac timings do not establish production performance.
Document transfer, ingestion/inference and VPN transit are outside this latency
gate, but their functional behavior remains required.

Local tests, actual-host tests and physical durability evidence are distinct.
At meaningful milestones, verify private access, real source accuracy, actual
phone/desktop flows, crash/stale-result/correction recovery, wake/readiness/leases,
backup during processing, NAS failures and isolated restore on the real hosts.
Use fault simulation without deliberate power cuts. All relevant functional and
recovery checks must pass before claiming a deployed release; failures and untested
requirements remain explicit. Do not waive a failed requirement silently.

## Out of Scope

- Additional users, public exposure, general household documents, OCR, email or
  automatic ingestion, arbitrary bank layouts and password-unlocking workflows.
- Revolut joint accounts, non-GBP ledgers and crypto holdings/transactions; their
  GBP-side movements in included accounts remain subject to this specification.
- FX portfolio conversion, detailed spending categories, budgets, financial advice,
  conversational/semantic/deep search, a separate mobile app or React frontend.
- A cash-wallet ledger, bulk review approval, queue-size wake triggers, forced
  laptop sleep, separate queue/search infrastructure and microservice expansion.
- NAS-hosted project compute/live database, automatic historical purging or
  old-original archival, elaborate/off-site backup infrastructure.
- Application implementation, provisioning, running benchmarks, destructive data
  changes or deployment as part of writing this specification. Those are later
  tasks. Publishing this local document does not authorize Git push.

## Further Notes

### Baseline and reference material

- [HLD](../../beng-document-intelligence-hld.md) and [domain glossary](../../GLOSSARY.md).
- [Resolved design map](../initial-release-design/map.md), including all twelve decisions and their evidence.
- [Storage ADR](../../docs/adr/0001-local-authority-and-nas-backups.md) and [application stack ADR](../../docs/adr/0002-python-application-and-rendered-ui.md).
- [Inspected source formats](../initial-release-design/research/statement-format-inventory.md) and [invented reporting/validation examples](../initial-release-design/research/import-contract-examples.md).
- [Model contract/evaluation prerequisite](../initial-release-design/issues/11-local-interpretation-and-model-evaluation.md) and [approved test interfaces/gates](../initial-release-design/issues/12-public-test-interfaces-and-release-acceptance.md).

The user supplied private originals outside the repository. Keep private oracle
values and statements there; version-control only synthetic/sanitized artifacts.
Existing diagrams labelled historical do not supersede the current HLD/design.
If this synthesis exposes a conflict, use the latest explicit user decision and
record the correction before implementing a changed policy.

### Explicit prerequisites for implementation tickets

| ID | Work to specify/verify | Required before |
| --- | --- | --- |
| P-01 | Prepare the selected Docker Desktop Mac test runtime, with real PostgreSQL and isolated files. | Database-dependent local tests. |
| P-02 | Pin compatible runtime/dependency/container versions; specify application schema, result formats, locators, durable original/record recovery and publication/claim mechanisms. | Corresponding implementation slices. |
| P-03 | Create supported-layout fixtures and independent expected results; establish any text/CSV support explicitly; add overlap/year-boundary evidence. | Enabling each extraction or automated matching rule. |
| P-04 | Obtain mini-PC local and NAS destination paths; verify headroom, local filesystem/flush behavior and the intended Docker daemon without changing existing services. | Provisioning and any durability claim. |
| P-05 | Verify the selected LAN-only hostname/direct-HTTP route, worker credential handling and controller adapter. Private HTTPS/VPN remains deferred before broadening access. Controller page-token protocol was verified read-only. | Selected real-host integration; no public exposure. |
| P-06 | Calibrate heartbeat/expiry, retry delays, execution/advice timeouts, readiness probes and cap-aware keep-awake behavior; retain accepted bounded failure semantics. | Actual-host job/power acceptance. |
| P-07 | Specify and prove consistent backup construction, success/retirement, catch-up/DST behavior and isolated restoration. | Backup/recovery release gate. |
| P-08 | Execute bounded local model/runtime selection with independent hold-out results. | Enabling optional advice, not shipping deterministic/manual-review capability. |

These are tracked prerequisite work, not claims that setup or testing has been
completed. New consequential policy changes still require Sourav's decision.
Next break this specification into dependency-ordered, end-to-end implementation
and test tickets. Each ticket must identify its approved test interface, independent
expected behavior, appropriate local checks and actual-host acceptance where
needed. Do not substitute a layer-by-layer build for usable vertical slices.

Local coherent commits are permitted under project instructions. Keep local
agent memory out of staging/commits. Push only after a completed milestone and
explicit approval; no pull request is required. Deployment or migrations affecting
existing data retain their separate approval requirements.
