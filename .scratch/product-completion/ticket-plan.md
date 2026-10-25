# Authoritative product-completion implementation backlog

Authority: ACTIVE — sole implementation direction.
Approval: Sourav approved the seventeen-task division and this authoritative cutover.
Execution: AUTHORIZED by Sourav: “Start implementation from .scratch/product-completion/ticket-plan.md”. Work the eligible frontier; unresolved decisions and separate live-operation/push approvals remain gates.

Read [the completion specification](spec.md) for scope, decisions and completion rules. Authorization above supersedes publication-time PAUSED text in individual tasks without resolving their design/input gates. Tasks01/02 are done locally; task03 is claimed by Codex.

## Active tasks

Published IDs are dependency-ordered. Draft T12 becomes10, T10 becomes11, T11 becomes12; all other numbers are unchanged. This is only numbering, not a change to the approved division. The draft-reference column preserves discussion traceability.

| Active task | Approved draft ID | Technical blockers | Planning readiness |
| --- | --- | --- | --- |
| [01 — First-use account and upload journey](issues/01-first-use-account-and-upload-journey.md) | T01 | None | done locally |
| [02 — Evidence-first dashboard and transaction navigation](issues/02-evidence-first-dashboard-and-transaction-navigation.md) | T02 | None | done locally |
| [03 — Source-first review and reversible decisions](issues/03-source-first-review-and-reversible-decisions.md) | T03 | None | done locally |
| [04 — Understand and recover an upload's processing state](issues/04-understand-and-recover-an-upload-s-processing-state.md) | T04 | None | done locally |
| [05 — Isolated laptop inference runtime and worker connectivity](issues/05-isolated-laptop-inference-runtime-and-worker-connectivity.md) | T05 | None | local code done; needs laptop deployment |
| [06 — One validated suggestion through explicit user confirmation](issues/06-one-validated-suggestion-through-explicit-user-confirmation.md) | T06 | 05 | implementation done; needs real-runtime demo |
| [07 — Advisory failure and separate bounded recovery](issues/07-advisory-failure-and-separate-bounded-recovery.md) | T07 | 06 | done locally |
| [08 — Qualify the model and gate enablement](issues/08-qualify-the-model-and-gate-enablement.md) | T08 | 05, 06, 07 | needs-info (labels + laptop) |
| [09 — Preserve financial results and corrections across interruptions](issues/09-preserve-financial-results-and-corrections-across-interruptions.md) | T09 | None | done locally |
| [10 — Consistent scheduled backup with safe retention](issues/10-consistent-scheduled-backup-with-safe-retention.md) | T12 | None | local proof done; needs NAS run |
| [11 — Qualify real-host scheduling, wake and keep-awake lifecycle](issues/11-qualify-real-host-scheduling-wake-and-keep-awake-lifecycle.md) | T10 | 09, 08 | needs-info |
| [12 — Actionable operational status without private logging](issues/12-actionable-operational-status-without-private-logging.md) | T11 | 04, 07, 09, 10 | done locally |
| [13 — Restore and verify a recovery generation in isolation](issues/13-restore-and-verify-a-recovery-generation-in-isolation.md) | T13 | 10 | local proof done; needs NAS run |
| [14 — Verify actual supplied statement families end to end](issues/14-verify-actual-supplied-statement-families-end-to-end.md) | T14 | 09 | synthetic pass; needs private sources |
| [15 — Measure and meet real-host dashboard/search latency](issues/15-measure-and-meet-real-host-dashboard-search-latency.md) | T15 | 02 | harness ready; needs mini-PC run |
| [16 — Accept complete desktop, keyboard and actual-phone journeys](issues/16-accept-complete-desktop-keyboard-and-actual-phone-journeys.md) | T16 | 01, 02, 03, 04, 07, 08, 12 | local audit pass; needs phone/deployment |
| [17 — Integrated release qualification and operating handoff](issues/17-integrated-release-qualification-and-operating-handoff.md) | T17 | 11, 13, 14, 15, 16 | ledger drafted; host gates open |

Task11's08 dependency gates final combined-workload timing acceptance; approved parser/controller investigation can start earlier after09. Host deployment, power/fault tests and final release are independently permission-gated. None/ready does not mean authorized.

## Working order after authorization

- Initial technical frontier:01–05,09,10, subject to each decision/input gate. Ready planning status currently applies to01–04,09,12;12 still has task dependencies.
- Inference:05 →06 →07 →08. Isolated evaluation is allowed only under its explicit authorization; normal-use enablement waits for08.
- Recovery:10 →13. Processing qualification:09 plus08 →11.
- Operational integration:04,07,09,10 →12. UI acceptance:01–04,07,08,12 →16.
- Financial/source acceptance:09 →14. Performance:02 →15. Final integrated acceptance:11,13–16 →17.
- One integration owner coordinates shared UI/advice/state changes. Choose eligible tasks, not an artificial serial dependency between independent work.

## Requirements coverage

AC identifiers refer to the retained [original requirements baseline](../initial-release/spec.md). Task17 owns final evidence reconciliation; producer tasks below own remaining implementation/verification. Historical completed behavior is reused, not reopened automatically.

| Acceptance criterion | Active delivery/verification owners | Final evidence owner |
| --- | --- | --- |
| AC-01 | 01, 04, 14, 16 | 17 |
| AC-02 | 01, 14 | 17 |
| AC-03 | 01, 14 | 17 |
| AC-04 | 01, 11, 13 | 17 |
| AC-05 | 14 | 17 |
| AC-06 | 09, 14 | 17 |
| AC-07 | 03, 14 | 17 |
| AC-08 | 02, 03, 14 | 17 |
| AC-09 | 03, 14 | 17 |
| AC-10 | 03, 14 | 17 |
| AC-11 | 01, 02, 16 | 17 |
| AC-12 | 02, 16 | 17 |
| AC-13 | 03, 09, 16 | 17 |
| AC-14 | 04, 11 | 17 |
| AC-15 | 04, 09, 11 | 17 |
| AC-16 | 09, 11 | 17 |
| AC-17 | 09, 14 | 17 |
| AC-18 | 11 | 17 |
| AC-19 | 01, 10, 12 | 17 |
| AC-20 | 04, 09, 11, 12 | 17 |
| AC-21 | 10 | 17 |
| AC-22 | 13 | 17 |
| AC-23 | 10, 12 | 17 |
| AC-24 | 02 | 17 |
| AC-25 | 06, 07, 16 | 17 |
| AC-26 | 05, 08 | 17 |
| AC-27 | 15 | 17 |

## Historical work disposition

All thirty initial-release implementation tickets are retired from execution, with a banner on every file. Completed tickets01–05,07–17,20 retain their done status and evidence. Other historical statuses describe their last recorded state, not an actionable queue or a false completion. Outstanding work belongs only to active tasks below. Historical claims are released. No implementation code is reverted.

| Historical ticket | Active successor / acceptance owner |
| --- | --- |
| [01](../initial-release/issues/01-open-a-private-local-account-overview.md) | 01 |
| [02](../initial-release/issues/02-preserve-an-upload-and-reopen-its-original.md) | 01 |
| [03](../initial-release/issues/03-explain-intake-rejection-and-account-mismatches.md) | 01 |
| [04](../initial-release/issues/04-process-an-assigned-upload-through-the-worker-interface.md) | 04, 09, 11 |
| [05](../initial-release/issues/05-import-lloyds-current-into-a-source-linked-transaction-view.md) | 14 |
| [06](../initial-release/issues/06-verify-the-first-private-deployment-milestone.md) | 11, 14 |
| [07](../initial-release/issues/07-import-lloyds-credit-with-posting-dates-and-separate-fees.md) | 14 |
| [08](../initial-release/issues/08-import-amex-without-duplicating-annual-or-fx-totals.md) | 14 |
| [09](../initial-release/issues/09-import-revolut-personal-gbp-while-ignoring-excluded-sections.md) | 14 |
| [10](../initial-release/issues/10-add-savings-mapping-and-independent-account-section-outcomes.md) | 14 |
| [11](../initial-release/issues/11-explain-spending-income-outgoing-and-net-cash-totals.md) | 02, 03, 14 |
| [12](../initial-release/issues/12-show-dated-balances-and-gap-aware-period-history.md) | 02 |
| [13](../initial-release/issues/13-search-descriptions-and-drill-into-metric-evidence.md) | 02 |
| [14](../initial-release/issues/14-review-and-reverse-a-correction-without-losing-history.md) | 03 |
| [15](../initial-release/issues/15-resolve-overlapping-imports-conservatively.md) | 03, 14 |
| [16](../initial-release/issues/16-confirm-repayments-and-own-account-transfer-links.md) | 03, 14 |
| [17](../initial-release/issues/17-apply-cash-refunds-fee-waivers-and-conversion-returns.md) | 03, 14 |
| [18](../initial-release/issues/18-recover-expired-worker-claims-and-bounded-core-retries.md) | 04, 09, 11 |
| [19](../initial-release/issues/19-fence-stale-results-and-preserve-corrections-across-lost-acknowledgements.md) | 09 |
| [20](../initial-release/issues/20-release-nightly-work-and-show-process-now-progress.md) | 04, 11 |
| [21](../initial-release/issues/21-integrate-bounded-laptop-wake-and-keep-awake-leases.md) | 11 |
| [22](../initial-release/issues/22-expose-operational-failures-without-logging-private-contents.md) | 12 |
| [23](../initial-release/issues/23-complete-phone-and-accessible-browser-journeys.md) | 01, 02, 03, 04, 16 |
| [24](../initial-release/issues/24-create-consistent-backup-generations-with-visible-failure.md) | 10 |
| [25](../initial-release/issues/25-restore-originals-records-and-corrections-into-isolation.md) | 13 |
| [26](../initial-release/issues/26-measure-and-meet-dashboard-and-search-latency.md) | 15 |
| [27](../initial-release/issues/27-show-validated-optional-advice-without-risking-financial-imports.md) | 05, 06, 07 |
| [28](../initial-release/issues/28-evaluate-up-to-two-local-advice-candidates-before-enablement.md) | 05, 08 |
| [29](../initial-release/issues/29-qualify-the-complete-deterministic-release-on-real-hosts.md) | 14, 16, 17 |
| [30](../initial-release/issues/30-record-release-evidence-and-a-reviewable-milestone-handoff.md) | 17 |

The old [ticket plan](../initial-release/ticket-plan.md) and [completion proposal](../initial-release/completion-plan.md) are retired. The original requirements, HLD, glossary and accepted ADRs are retained, not deprecated as completed tasks. The design decision map remains historical design rationale, not an implementation queue.

## Next planning action

Resolve D1–D3 using available repository/authorized host evidence and focused user tradeoff decisions; collect D4 external acceptance prerequisites before the relevant live work. Eligible implementation may now proceed under Sourav's explicit instruction; unresolved decisions remain gates.
