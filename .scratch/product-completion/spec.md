# Product completion: authoritative implementation specification

Planning approval: Sourav approved the seventeen-task division and requested this backlog become the active authoritative implementation direction.
Execution authorization: Sourav explicitly instructed implementation from this backlog. Eligible local implementation may proceed; unresolved decision gates and separate deployment/live-data/power/push permissions remain in force.

## Authority and scope

Start with [the active task index](ticket-plan.md). Only this directory's seventeen tickets are active implementation work. The previous initial-release execution plan, completion proposal and thirty implementation tickets are historical evidence, not another work queue. Retain their original completion records; never repeat completed work merely because a new ticket links to it.

The [HLD](../../beng-document-intelligence-hld.md), [glossary](../../GLOSSARY.md), accepted [authority ADR](../../docs/adr/0001-local-authority-and-nas-backups.md), [stack ADR](../../docs/adr/0002-python-application-and-rendered-ui.md), and [original requirements and AC-01–27](../initial-release/spec.md) remain requirements sources. This specification governs remaining execution, approved refinements and release gates; it does not replace established financial semantics. Escalate substantive conflicts rather than silently reinterpret them.

Completion means a usable responsive product, qualified local advisory inference, reliable processing, verified backup/restore, financial correctness and actual-host acceptance. A failed model evaluation requires Sourav's explicit disposition; deterministic-only completion is not automatic.

## Approved refinements

- Visual direction A: overview rail, metric-first dashboard and source/decision review; responsive Django pages, not a React rewrite. Retain the existing evidence-only SVG chart for this slice rather than migrate chart libraries without a concrete need. This is a scoped refinement of the original Chart.js selection, not a change to reporting semantics.
- Account onboarding includes create/list/select and first-upload guidance. Account deletion, renaming and type changes are outside these tasks unless separately agreed.
- Reuse existing parser/report/review/job work and audit preserved UI changes. Do not treat the interrupted UI work as accepted or complete.
- Local integrity/recovery (09) is independent of actual-host calibration (11). Both remain mandatory. Host prerequisites do not stall unrelated local tasks.
- LAN-only deployment on the mini-PC; no reverse-proxy/TLS/VPN project added by implication. Existing authentication remains; LAN-only is not permission to remove it.
- Mini-PC owns authoritative PostgreSQL, originals and updates. Laptop worker uses its API; NAS stores recovery copies, not live database or compute. Project application/worker/database deployment remains Docker-based.
- Original financial facts are deterministic and immutable to advice. Source, processing history and corrections remain traceable. No cloud inference, private source fixtures or credentials in Git.

## Decision register

Open decisions are explicit gates, not incomplete implementation instructions to guess through. Evidence gathering and written design can continue in planning; code, model runs/downloads, installation and host mutation require separate approval. Update the affected task's status only after its missing design/input is resolved. Authorization remains separate.

| Gate | Affected tasks | Proposed direction / facts | Required closure evidence |
| --- | --- | --- | --- |
| D1: inference deployment and candidate | 05,08 | **Deployment choice resolved:** Sourav selected a dedicated Docker inference service. Pin runtime/model independently; leave existing native Ollama and its consumers untouched. Installed models are not qualified candidates. | Remaining: primary-source license/structured-output/capacity checks for at most two candidates; documented ports, GPU/memory allocation and worker-container connectivity. Installation/download permission must be separately recorded. |
| D2: advisory contract and evaluation | 06,07,08 | Versioned classification/abstention with source references, short explanation, model/prompt identity; mini-PC validates, user confirms; separate bounded advice recovery. | Written source/correction revision binding, stale-result rule, dismissal/retry behavior, timeout/cap, provenance/retention and independently established development/held-out label protocol. User-approved tradeoffs before implementation. |
| D3: recovery consistency and destination | 10,13 | Seven complete generations at03:00 Europe/London; no live database-directory copy, no local deletion. Prefer a consistent PostgreSQL snapshot plus the exact associated immutable originals and a completion manifest. | Specify snapshot/original consistency protocol, partial-generation detection, atomic publication/retirement, restore verification, NAS path/headroom/permissions and failure handling; agree any write interruption. Live target changes require approval. |
| D4: external acceptance prerequisites | 11,13–17 | Existing mini-PC/laptop setup is user-reported; localhost evidence is not target acceptance. | Read-only inventory and private source/oracle availability; approved isolated deployment/storage/resources, power/fault window, physical phone participation and final release sign-off. No routine request for facts already obtainable from repo/authorized host inspection. |

These gates are not a second implementation backlog. Resolve them and record the decisions here and in an ADR only when the tradeoff warrants it. Tasks with missing design or external inputs use `needs-info`; others may use `ready-for-agent`. Implementation is authorized only where those prerequisites and true task blockers are satisfied.

## Completion rules

1. Before starting any task, require explicit implementation authorization, resolved design gates and completed true blockers. Task11's model dependency gates final combined-workload acceptance, not earlier parser/controller investigation.
2. Read the task, requirements and linked historical evidence. Identify actual gaps; preserve unrelated changes and existing originals/data.
3. Each task owns an end-to-end behavior, its meaningful public-interface tests, integration and an observable runtime/browser demonstration. Use TDD for changed behavior; don't invent tests for documentation or reuse model outputs as expected financial results.
4. Review both project standards and specification compliance. Independent review must have explicit ownership; shared review UI and advice changes must be integrated by one owner. Dependency independence alone does not permit conflicting edits.
5. Record local results separately from real-host/device results, exact exercised commands/scenarios, limits and commit references. Passing tests or service uptime alone cannot close a required host/model/restore/phone acceptance gate.
6. Close only after all ticket criteria and required gates pass. A blocked task stays open; a failed model benchmark cannot silently reduce release scope.
7. Deployment, migrations affecting existing data, destructive actions, power/fault exercises and push retain separate explicit approval. Never seed synthetic benchmark data into the live database or restore over it for a test.

## Baseline and preserved work

Historical implementation: initial-release01–05,07–17 and20 record completed local behavior. Other historical tickets include partial implementation or unresolved qualification. Their evidence remains in place.

The most recent UI/account work is unaccepted, uncommitted WIP. A257-test run passed before later presentation edits; local browser account creation, upload, worker import, dashboard/drilldown/search and review rendering were observed. Final correction/revert and narrow-screen verification were interrupted. None of this establishes actual-phone or deployed UI acceptance. Preserve the work and audit it under tasks01–04; no implementation resumes merely because these files exist.
