# Public test interfaces and release acceptance

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 08, 09, 10, 11
Parent: [Initial release technical design](../map.md)

## Question

Agree the public behavior interfaces for TDD, representative fixture dataset,
financial/failure/recovery cases, and first-release acceptance. Refine the map's
provisional history/volume and two-second response targets into measurable
conditions, including what partial data and local-model evaluation can prove.

## Resolution evidence

User-approved test interfaces (what they catch and miss), explicit performance
measurement conditions, and real-host acceptance gates for NAS/wake/recovery/
model behavior. Ready to hand off linked decisions to `/to-spec`, not to skip
directly into application implementation.

## Agreed testing direction

Sourav confirmed the Mac is the development host and should run as many
appropriate tests as possible. Full actual-deployment end-to-end checks happen
at meaningful milestones. Local runtime provisioning remains open; do not infer
local Docker installation or native database approval from this direction.

## Confirmed test interfaces and release gates

Sourav accepted Q73-Q76. These approve the test interfaces and criteria, not
execution or deployment.

Q73 accepted public test seams:

| Seam | Catches | Misses |
| --- | --- | --- |
| Public statement interpretation/reporting interface | Layout/date/sign normalization, reconciliation, reporting arithmetic and rules using independent fixtures | DB transactions, browser wiring and physical hosts |
| Application upload/job/result/review/report interfaces with real PostgreSQL and isolated files | Preservation, ownership/idempotency, correction precedence, section publication, actual persistence and authorization | Real GPU/power controller and browser rendering |
| Browser journeys | Login, upload/status, metric/source drilldown, search and review in desktop/narrow viewports | Physical phone behavior and real hardware faults unless exercised there |
| Infrastructure adapters/operational commands | Controlled failure contracts plus real-host wake/leases, backup/restore and restart acceptance | Fakes do not establish physical behavior; restart tests do not prove power-loss durability |

Use no private-method tests or DB side-channel assertions; observe public results.
External systems and clocks may be controlled for local failure tests; real DB/file
behavior is exercised rather than replaced by mocks. No tests are written yet.

Q74 accepted: synthetic/sanitized fixtures for supported layouts and accepted edge cases,
with independently reviewed expected results and fixed seed for performance
history. Private originals remain external, optional for local checks but required
for four-format actual-source release verification; preserve actual coverage gaps.
No full-August oracle inferred from mismatched card cycles. Model pilot dataset
remains distinct from deterministic parser expectations.

Q75 accepted: 100,000 transactions across up to ten years, one active user; home-LAN
actual-mini-PC dashboard/period-update and simple description-search interactions
p95 <=2 seconds, submission to visible usable result. At least 30 timed repetitions
per representative journey after one warm-up; record cold first load separately.
Record dataset/query/range/browser/network/runtime conditions; exclude document
file transfer, ingestion/inference and VPN transit from this specific latency gate,
not from functional acceptance. Mac measurements do not establish host performance.

Q76 accepted: require local behavioral tests and meaningful actual-host E2E milestones,
including supplied-format private oracle checks, LAN/VPN authentication, core
phone/desktop journeys, restart/stale-result/correction recovery, wake/readiness/
lease lifecycle, independent backups during processing, NAS failure visibility and
isolated restore with originals/evidence/corrections. Use fault simulation rather
than deliberate power cuts; no guarantee of flush safety from restart testing.
Advice enabled only after its separate benchmark; otherwise manual review allowed.
All required functional/recovery tests must pass before deployed-release claims;
record failures/untested items, do not silently waive them. Provisioning/runtime,
paths/secrets and deployment actions remain later work under existing approval
rules. Milestone completion still does not authorize a push.

## Answer

The four public test seams, independent fixture/oracle policy, measurable
performance target and local/actual-host release gates are accepted. This is the
final design decision; the map can hand off to specification and vertical
implementation/test tickets. No test suite, performance measurement, successful
restore, model benchmark or deployed-release verification is claimed.

Specification/tickets must retain the approved interfaces and catch/miss limits,
translate HLD scenarios and import examples into independently expected outcomes,
and carry provisioning, private routing/credentials, actual model selection and
calibrated timing as explicit prerequisites. Those tasks are not silently done.
Local runtime setup must be chosen before tests require PostgreSQL; production
Docker constraints do not imply that a Mac Docker runtime is already selected.

Follow one failing behavioral test with its minimum implementation per cycle.
Do not create all tests in advance or inspect private methods/DB internals as a
substitute for observable behavior. Evidence distinguishes Mac tests, controlled
failure tests, actual-host checks and physical durability limits. No push is
authorized by this design milestone.
