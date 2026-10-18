# Worker jobs, retries, and result publication

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 05, 06
Parent: [Initial release technical design](../map.md)

## Question

Define the authenticated application/worker job, source-read, and result
interfaces. Resolve claiming, expiry/heartbeat, retries, cancellation if needed,
result identity/versioning, stale-result rejection, correction precedence and
atomic publication. Show recovery after crash, lost result acknowledgement,
repeated Process now, and worker disappearance without duplicate effects.

## Resolution evidence

Agreed public contracts and observable state/recovery scenarios, using the
chosen application/storage capabilities without a separate queue service.

## Evidence to consult

[Controller inventory](../research/host-storage-wake-inventory.md) distinguishes
cached agent availability from application-worker readiness. It also identifies
possible expiring sleep-inhibition leases. Decide whether/how active processing
keeps the laptop awake, without taking ownership of forcing sleep afterward.

## Discussion history

Q40-Q42 proposals awaiting Sourav: one upload per job and one active worker job;
source/result traffic through authenticated application APIs with temporary local
worker files; jobs become eligible only through nightly batching or Process now,
even if the laptop is already awake. Scope of Process now proposed as all pending
uploads without interrupting current work. Retry/lease/publication details follow
after these choices; none is approved by merely claiming the ticket.

### Confirmed first round

Sourav accepted Q40-Q42: one upload per job, one job at a time initially. Worker
downloads assigned originals through an authenticated application endpoint and
submits structured results via API; temporary laptop files are cleaned on normal
completion and after crashes. No shared folders or worker database credentials.
Authoritative originals stay on mini-PC.

Pending uploads are not automatically eligible merely because laptop is awake.
Nightly batching or Process now releases work. Process now releases all currently
waiting uploads, requests wake if needed, and neither interrupts running work
nor duplicates it on repeated clicks. Recovery/result publication details remain
open; this ticket is still claimed.

### Confirmed recovery round

Sourav accepted Q43-Q45:

- A job attempt holds a temporary claim renewed by periodic worker reports.
  After enough missed reports, the application may retry it. A worker stops
  when it detects lost ownership; an expired attempt's late result must not
  replace a newer attempt. Computation may repeat; committed financial effects
  must not. Claim timings and task execution timeouts remain tunable.
- Temporary network/worker/inference failures receive up to three processing
  attempts in total with increasing delays, then visible failure/manual retry.
  Unsupported formats and repeatable validation failures go directly to review.
  Wake/readiness checks do not consume upload processing attempts.
- Result submission has a stable attempt identity. If the application commits
  but acknowledgement is lost, repeating the identical submission returns the
  recorded success without applying effects twice. Conflicting content under
  the same identity is rejected. Publish only after validation commits.

### Confirmed correction and keep-awake round

Sourav accepted Q46-Q47 and requested inspection of the existing controller.
Machine-derived results remain separate from user corrections; publication
preserves confirmed values and flags contradictions. If changed transaction
identities prevent safe correction mapping, retain the prior published view
and request review.

Active processing uses a bounded expiring keep-awake lease, renewed only while
work is legitimately active and released on completion. A crash leaves a bounded
lease to expire. Never release unrelated user leases or force sleep.

Read-only page/capability and source inspection confirmed existing create,
extend and release actions. Extension adds to expiry with a ceiling eight hours
from creation; renewal must account for remaining lifetime and this ceiling.
See [existing keep-awake contract](../research/keep-awake-contract.md).
No target POSTs or changes were made; lease lifecycle and sleep prevention are
not yet tested. Concrete machine authentication belongs to the operating-policy
decision.

## Answer

The accepted rounds above define one upload per serial job, authenticated API
source/result exchange, explicit batch eligibility, renewable claims with stale
attempt fencing, three total transient processing attempts, idempotent atomic
result publication, correction precedence, and bounded active-work sleep
inhibition using the existing controller. The HLD reflects these contracts.

Decision complete following Sourav's acceptance. Timing calibration, concrete
API schemas/authentication, controller cap handling and fault-injection tests
remain specification/implementation work; this resolution does not claim a
working deployment.

## Later refinement: optional advisory failures

Q68 accepted in [Local interpretation contract and model evaluation](11-local-interpretation-and-model-evaluation.md)
refines the general inference retry clause above: optional LLM advice failure
must not discard validated deterministic results or repeat their import. Leave
unresolved items in review, show advice unavailable and retry advice separately
with bounds. Core job failures retain the three-attempt processing policy.
