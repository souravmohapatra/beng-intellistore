# First-release implementation tickets

Status: ready-for-agent
Publication: 30 individual tickets published following Sourav’s approval.

[Release specification](spec.md) remains the accepted scope; these tickets do not
modify it or start implementation. Each ticket includes the tests and integration
needed for its behavior. IDs are dependency ordered; they are not a requirement
to work a needless linear chain. No implementation agents have been launched. Each ticket targets one fresh,
focused implementation context; this is a sizing goal, not a guarantee that
hardware investigation or unexpected defects finish in a fixed time.

## Approved tickets

1. **[Open a private local account overview](issues/01-open-a-private-local-account-overview.md)** — Blocked by: None. Sourav can sign in locally and see named account slots and an honest empty dashboard backed by real PostgreSQL. **Stronger oversight.**
2. **[Preserve an upload and reopen its original](issues/02-preserve-an-upload-and-reopen-its-original.md)** — Blocked by: 01. A signed-in user can upload an original, receive a durable receipt, see it listed and reopen it after application restart. **Stronger oversight.**
3. **[Explain intake rejection and account mismatches](issues/03-explain-intake-rejection-and-account-mismatches.md)** — Blocked by: 02. The upload flow explains rejected files, preserves readable unsupported layouts and flags source/account mismatches. **Budget candidate.**
4. **[Process an assigned upload through the worker interface](issues/04-process-an-assigned-upload-through-the-worker-interface.md)** — Blocked by: 03. Process now releases a waiting upload to one worker, which downloads its assigned source and returns a visible validated outcome through the application. **Stronger oversight.**
5. **[Import Lloyds Current into a source-linked transaction view](issues/05-import-lloyds-current-into-a-source-linked-transaction-view.md)** — Blocked by: 04. A Lloyds Current upload is processed by the worker and appears as exact, dated transactions and balance observations with original evidence. **Budget candidate.**
6. **[Verify the first private deployment milestone](issues/06-verify-the-first-private-deployment-milestone.md)** — Blocked by: 05. An isolated project deployment on the actual mini-PC/laptop can privately upload and process a Lloyds Current statement and reopen its evidence. **Stronger oversight.**
7. **[Import Lloyds Credit with posting dates and separate fees](issues/07-import-lloyds-credit-with-posting-dates-and-separate-fees.md)** — Blocked by: 05. A Lloyds Credit upload shows billed purchases, payment credits, fees and debt evidence in the same transaction/evidence flow. **Budget candidate.**
8. **[Import Amex without duplicating annual or FX totals](issues/08-import-amex-without-duplicating-annual-or-fx-totals.md)** — Blocked by: 05. An Amex upload shows exact billed rows and credits using process dates, with evidence linked through the existing flow. **Budget candidate.**
9. **[Import Revolut personal GBP while ignoring excluded sections](issues/09-import-revolut-personal-gbp-while-ignoring-excluded-sections.md)** — Blocked by: 05. A consolidated Revolut original imports personal GBP rows and balances while clearly ignoring joint, non-GBP and crypto sections. **Budget candidate.**
10. **[Add savings mapping and independent account-section outcomes](issues/10-add-savings-mapping-and-independent-account-section-outcomes.md)** — Blocked by: 09. One Revolut upload populates personal GBP and savings GBP, preserving valid sections when another section fails validation. **Stronger oversight.**
11. **[Explain spending income outgoing and net cash totals](issues/11-explain-spending-income-outgoing-and-net-cash-totals.md)** — Blocked by: 05. The dashboard shows independently verifiable posting-period totals with explicit provisional classifications rather than simply adding source totals. **Budget candidate.**
12. **[Show dated balances and gap-aware period history](issues/12-show-dated-balances-and-gap-aware-period-history.md)** — Blocked by: 11. A user selects month/year/custom periods and sees dated account balances and net-cash history without fabricated continuity. **Budget candidate.**
13. **[Search descriptions and drill into metric evidence](issues/13-search-descriptions-and-drill-into-metric-evidence.md)** — Blocked by: 11. A user opens contributing transactions from a metric or searches original descriptions and reaches supporting originals with period context intact. **Budget candidate.**
14. **[Review and reverse a correction without losing history](issues/14-review-and-reverse-a-correction-without-losing-history.md)** — Blocked by: 11. A user resolves one issue beside source evidence and sees the effect of an explicit correction, with a validated history-preserving revert. **Stronger oversight.**
15. **[Resolve overlapping imports conservatively](issues/15-resolve-overlapping-imports-conservatively.md)** — Blocked by: 14. Repeated originals and overlapping sources avoid duplicate financial effects without collapsing genuine identical-looking transactions. **Stronger oversight.**
16. **[Confirm repayments and own-account transfer links](issues/16-confirm-repayments-and-own-account-transfer-links.md)** — Blocked by: 07, 08, 09, 14. A user reviews and confirms supported transfer/repayment candidates while both account entries remain traceable and reporting avoids double counting. **Stronger oversight.**
17. **[Apply cash refunds fee waivers and conversion returns](issues/17-apply-cash-refunds-fee-waivers-and-conversion-returns.md)** — Blocked by: 14. The reporting/review flow handles agreed cash and reversal cases, including Revolut FX spending at the GBP boundary. **Budget candidate.**
18. **[Recover expired worker claims and bounded core retries](issues/18-recover-expired-worker-claims-and-bounded-core-retries.md)** — Blocked by: 04. Interrupted processing becomes retryable without stale ownership or an endless retry loop, with visible recovery status. **Stronger oversight.**
19. **[Fence stale results and preserve corrections across lost acknowledgements](issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md)** — Blocked by: 14, 18. Results can be safely resubmitted after lost acknowledgements and cannot replace newer attempts or confirmed edits. **Stronger oversight.**
20. **[Release nightly work and show Process now progress](issues/20-release-nightly-work-and-show-process-now-progress.md)** — Blocked by: 04. Uploads release at 21:00 Europe/London or Process now, with visible asynchronous status and safe restart catch-up. **Budget candidate.**
21. **[Integrate bounded laptop wake and keep-awake leases](issues/21-integrate-bounded-laptop-wake-and-keep-awake-leases.md)** — Blocked by: 20. Eligible work wakes the laptop through the existing controller and maintains only its own bounded active-work inhibition. **Stronger oversight.**
22. **[Expose operational failures without logging private contents](issues/22-expose-operational-failures-without-logging-private-contents.md)** — Blocked by: 18, 20. The app shows actionable unresolved failures and last-success information while operational logs remain safe. **Budget candidate.**
23. **[Complete phone and accessible browser journeys](issues/23-complete-phone-and-accessible-browser-journeys.md)** — Blocked by: 12, 13, 14. Core dashboard, upload, search and one-at-a-time review work on narrow screens and desktop with clear visual hierarchy. **Budget candidate.**
24. **[Create consistent backup generations with visible failure](issues/24-create-consistent-backup-generations-with-visible-failure.md)** — Blocked by: 14. A 03:00 Europe/London backup produces a consistent original-plus-record recovery set and exposes its outcome without blocking normal use. **Stronger oversight.**
25. **[Restore originals records and corrections into isolation](issues/25-restore-originals-records-and-corrections-into-isolation.md)** — Blocked by: 24. A successful recovery generation restores into an isolated target with working source links and retained user corrections. **Stronger oversight.**
26. **[Measure and meet dashboard and search latency](issues/26-measure-and-meet-dashboard-and-search-latency.md)** — Blocked by: 06, 12, 13. On the actual mini-PC, representative dashboard and text-search interactions meet the agreed measurable latency gate. **Budget candidate.**
27. **[Show validated optional advice without risking financial imports](issues/27-show-validated-optional-advice-without-risking-financial-imports.md)** — Blocked by: 14. An unresolved review item can show a source-linked structured local classification suggestion, or remain usable when advice fails. **Budget candidate.**
28. **[Evaluate up to two local advice candidates before enablement](issues/28-evaluate-up-to-two-local-advice-candidates-before-enablement.md)** — Blocked by: 06, 27. A documented actual-laptop evaluation either selects a passing local candidate or records that advice stays disabled. **Stronger oversight.**
29. **[Qualify the complete deterministic release on real hosts](issues/29-qualify-the-complete-deterministic-release-on-real-hosts.md)** — Blocked by: 10, 15, 16, 17, 19, 21, 22, 23, 25, 26. The integrated deterministic application passes source accuracy, private access, phone, failure and recovery gates on deployment hosts. **Stronger oversight.**
30. **[Record release evidence and a reviewable milestone handoff](issues/30-record-release-evidence-and-a-reviewable-milestone-handoff.md)** — Blocked by: 29. Sourav can review exactly which release requirements passed, what remains disabled and the verified operate/recover procedure. **Stronger oversight.**

## Milestones

| Milestone | Demonstrable checkpoint | Tickets/gates |
| --- | --- | --- |
| First usable local slice | Login, preserve original, worker round trip and Lloyds Current evidence | 01–05 |
| First real-host milestone | Isolated private upload/process/source verification | 06; deployment approval required |
| Deterministic product | All four source families, included savings, reporting/search/review/matching and recovery/power behavior | Core tickets 07–23; follow dependencies |
| Recovery and qualification | NAS backup/isolated restore, measured latency and real-host integrated acceptance | 24–26 and 29–30, together with all core dependencies |
| Optional advice | Structured suggestions and bounded actual-laptop model evaluation | 27–28; not a blocker for manual-review release |

Milestones are checkpoints, not permission to push. Run real-host regression at
meaningful later checkpoints using the procedure established in the first host
ticket. Ticket 29 is final qualification, not the first hardware test.

## Execution proposal

Recommended workflow, not a multi-agent configuration already enabled:

1. A capable coordinator selects one approved unclaimed ticket whose blockers are
   done, checks prerequisites and gives the worker a narrow brief with expected
   behavior, agreed interface, scope exclusions and verification commands.
2. One implementation worker owns the working changes. Use a fresh focused context
   per ticket. Write one failing behavioral test, implement the minimum, repeat.
3. A stronger reviewer checks the diff against both the specification and project
   standards, and inspects whether assertions could miss financial/data-loss bugs.
   Passing tests alone is not completion. Fix findings and rerun affected checks.
4. Record evidence and make a coherent local commit; then mark the ticket done and
   select the next available ticket. At milestones run the specified actual-host
   checks and ask for push approval only after the milestone is verified.

Independent read-only review/research can overlap a worker only when explicitly
authorized by the user or an applicable skill. Do not interpret this document as
permission to spawn agents, change models or begin implementation. Parallel
coding is optional later for genuinely independent tasks with separate file
ownership or isolated checkouts and an integration owner. Dependency independence
alone does not prevent edit conflicts. No custom scheduler is needed initially. This recommendation follows the
[official multi-agent guidance](https://developers.openai.com/api/docs/guides/agents-api/multi-agent):
use delegation for independent work and keep dependent steps coordinated.

The first parser establishes a common contract. Lloyds Credit, Amex and Revolut
personal slices then have independent blockers (05), so they are possible later
parallel candidates once shared interfaces and file ownership are stable. Default
is still one coding worker at a time; review can be a separate pass in the same
chat until actual delegation/model routing is authorized.

## Budget-model guidance

Budget worker candidates are scope judgments, not measured guarantees of cost or
capability. No particular model or price tier is selected. Shared interface and
data-model decisions, authentication, durable preservation, concurrency, matching,
partial publication, backup/restore and deployment receive stronger oversight.
Even a budget candidate involving money needs independent expected values and
stronger review. A narrow ticket may still expose a hard bug or missing evidence.

Pilot the approach on one established-pattern ticket after the first vertical
slice. Compare correctness, review corrections, reruns and total effort. If it
needs repeated repair, promote the task to a stronger model or split around a
concrete newly discovered behavior; do not force every task onto the cheap tier.
Do not write tests with a stronger model and all implementation later: the worker
owns the vertical TDD loop, while the reviewer independently validates it.

The optional app-local LLM is distinct from the coding assistant. Coding-model
selection does not change the prohibition on cloud processing in the released app.

## Common completion rules

- Read the spec, glossary, relevant ADRs and ticket before work. Confirm a new
  test interface only if it changes the four already approved interfaces.
- Keep tests with each ticket. Never build all schemas, then all APIs, then all
  screens; a completed ticket has an observable journey or operational result.
- Keep real PostgreSQL/files for persistence tests; control external clocks and
  systems at approved interfaces. Expected values do not come from the parser.
- Keep private originals and labels outside Git. No synthetic success for an
  unrun backup, restore, power action, phone check or model benchmark.
- Resolve runtime/path/credential/deployment prerequisites before dependent work;
  tickets with operational prerequisites are not authorization to mutate hosts.
- Use only owned local/project state for fault tests; no deliberate power cuts,
  unrelated service changes, vendor DB reuse or forced laptop sleep.
- Local commits are permitted; staging must exclude local agent memory and
  private data. Push requires completed milestone and explicit approval.

## Coverage and blockers

| Release acceptance | Delivery/verification owners |
| --- | --- | --- |
| AC-01 | [01](issues/01-open-a-private-local-account-overview.md), [04](issues/04-process-an-assigned-upload-through-the-worker-interface.md), [06](issues/06-verify-the-first-private-deployment-milestone.md), [13](issues/13-search-descriptions-and-drill-into-metric-evidence.md); final integrated verification in 29/30. |
| AC-02 | [02](issues/02-preserve-an-upload-and-reopen-its-original.md), [03](issues/03-explain-intake-rejection-and-account-mismatches.md), [09](issues/09-import-revolut-personal-gbp-while-ignoring-excluded-sections.md), [10](issues/10-add-savings-mapping-and-independent-account-section-outcomes.md); final integrated verification in 29/30. |
| AC-03 | [03](issues/03-explain-intake-rejection-and-account-mismatches.md); final integrated verification in 29/30. |
| AC-04 | [02](issues/02-preserve-an-upload-and-reopen-its-original.md), [06](issues/06-verify-the-first-private-deployment-milestone.md); final integrated verification in 29/30. |
| AC-05 | [05](issues/05-import-lloyds-current-into-a-source-linked-transaction-view.md), [06](issues/06-verify-the-first-private-deployment-milestone.md), [07](issues/07-import-lloyds-credit-with-posting-dates-and-separate-fees.md), [08](issues/08-import-amex-without-duplicating-annual-or-fx-totals.md), [09](issues/09-import-revolut-personal-gbp-while-ignoring-excluded-sections.md); final integrated verification in 29/30. |
| AC-06 | [04](issues/04-process-an-assigned-upload-through-the-worker-interface.md), [15](issues/15-resolve-overlapping-imports-conservatively.md), [19](issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md); final integrated verification in 29/30. |
| AC-07 | [15](issues/15-resolve-overlapping-imports-conservatively.md); final integrated verification in 29/30. |
| AC-08 | [07](issues/07-import-lloyds-credit-with-posting-dates-and-separate-fees.md), [08](issues/08-import-amex-without-duplicating-annual-or-fx-totals.md), [11](issues/11-explain-spending-income-outgoing-and-net-cash-totals.md), [16](issues/16-confirm-repayments-and-own-account-transfer-links.md); final integrated verification in 29/30. |
| AC-09 | [17](issues/17-apply-cash-refunds-fee-waivers-and-conversion-returns.md); final integrated verification in 29/30. |
| AC-10 | [09](issues/09-import-revolut-personal-gbp-while-ignoring-excluded-sections.md), [10](issues/10-add-savings-mapping-and-independent-account-section-outcomes.md), [16](issues/16-confirm-repayments-and-own-account-transfer-links.md), [17](issues/17-apply-cash-refunds-fee-waivers-and-conversion-returns.md); final integrated verification in 29/30. |
| AC-11 | [01](issues/01-open-a-private-local-account-overview.md), [10](issues/10-add-savings-mapping-and-independent-account-section-outcomes.md), [11](issues/11-explain-spending-income-outgoing-and-net-cash-totals.md), [12](issues/12-show-dated-balances-and-gap-aware-period-history.md), [23](issues/23-complete-phone-and-accessible-browser-journeys.md); final integrated verification in 29/30. |
| AC-12 | [13](issues/13-search-descriptions-and-drill-into-metric-evidence.md), [23](issues/23-complete-phone-and-accessible-browser-journeys.md); final integrated verification in 29/30. |
| AC-13 | [14](issues/14-review-and-reverse-a-correction-without-losing-history.md), [15](issues/15-resolve-overlapping-imports-conservatively.md), [16](issues/16-confirm-repayments-and-own-account-transfer-links.md), [19](issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md), [23](issues/23-complete-phone-and-accessible-browser-journeys.md); final integrated verification in 29/30. |
| AC-14 | [04](issues/04-process-an-assigned-upload-through-the-worker-interface.md), [20](issues/20-release-nightly-work-and-show-process-now-progress.md); final integrated verification in 29/30. |
| AC-15 | [04](issues/04-process-an-assigned-upload-through-the-worker-interface.md), [18](issues/18-recover-expired-worker-claims-and-bounded-core-retries.md); final integrated verification in 29/30. |
| AC-16 | [18](issues/18-recover-expired-worker-claims-and-bounded-core-retries.md), [19](issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md); final integrated verification in 29/30. |
| AC-17 | [04](issues/04-process-an-assigned-upload-through-the-worker-interface.md), [05](issues/05-import-lloyds-current-into-a-source-linked-transaction-view.md), [10](issues/10-add-savings-mapping-and-independent-account-section-outcomes.md), [19](issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md); final integrated verification in 29/30. |
| AC-18 | [21](issues/21-integrate-bounded-laptop-wake-and-keep-awake-leases.md); final integrated verification in 29/30. |
| AC-19 | [02](issues/02-preserve-an-upload-and-reopen-its-original.md), [06](issues/06-verify-the-first-private-deployment-milestone.md), [22](issues/22-expose-operational-failures-without-logging-private-contents.md), [24](issues/24-create-consistent-backup-generations-with-visible-failure.md); final integrated verification in 29/30. |
| AC-20 | [18](issues/18-recover-expired-worker-claims-and-bounded-core-retries.md), [20](issues/20-release-nightly-work-and-show-process-now-progress.md), [22](issues/22-expose-operational-failures-without-logging-private-contents.md); final integrated verification in 29/30. |
| AC-21 | [24](issues/24-create-consistent-backup-generations-with-visible-failure.md); final integrated verification in 29/30. |
| AC-22 | [25](issues/25-restore-originals-records-and-corrections-into-isolation.md); final integrated verification in 29/30. |
| AC-23 | [22](issues/22-expose-operational-failures-without-logging-private-contents.md), [24](issues/24-create-consistent-backup-generations-with-visible-failure.md); final integrated verification in 29/30. |
| AC-24 | [12](issues/12-show-dated-balances-and-gap-aware-period-history.md); final integrated verification in 29/30. |
| AC-25 | [27](issues/27-show-validated-optional-advice-without-risking-financial-imports.md); final integrated verification in 29/30. |
| AC-26 | [28](issues/28-evaluate-up-to-two-local-advice-candidates-before-enablement.md); conditional advice enablement only, disposition recorded in 30. |
| AC-27 | [26](issues/26-measure-and-meet-dashboard-and-search-latency.md); final integrated verification in 29/30. |

Every acceptance criterion has a delivery owner and final evidence owner.
For a deterministic/manual-review release, advice stays disabled and its advice-only
behavior/quality gates are explicitly inactive rather than claimed passed; core
manual review and successful imports without a model are still required. The
eight spec prerequisites are carried into relevant tickets (P-01 in 01; P-02 in
01/02/04/10/14/19; P-03 in 03/05/07–10/15–17; P-04 in 06/24; P-05 in
06/21; P-06 in 18/20/21/27; P-07 in 24/25; P-08 in 28); paths, deployment
approval, local runtime choice, extra format/overlap evidence, device access and
independent model labels are real prerequisites, not silently completed work.

## Approval and next action

Sourav approved this breakdown and requested a local commit as the end-of-planning
checkpoint. All thirty tickets are published with ready-for-agent status; their
blockers and operational prerequisites still apply. No application implementation
or delegation has started. Execution/model routing remains a recommendation.

Next begin Open a private local account overview, resolving the Mac runtime
prerequisite before database-dependent tests or installation. Local commit of this
planning checkpoint does not authorize push or deployment.
