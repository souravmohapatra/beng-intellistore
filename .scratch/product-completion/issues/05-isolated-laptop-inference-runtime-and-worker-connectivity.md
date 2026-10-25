# 05: Isolated laptop inference runtime and worker connectivity

Status: needs-info
Approval: task division approved by Sourav; planning/publication only.
Execution authorization: PAUSED — requires Sourav's explicit implementation instruction.
Blocked by: None (technical dependencies only; authorization still required)
Draft reference: T05
Parent: [Authoritative completion specification](../spec.md)
Historical evidence: [27](../../initial-release/issues/27-show-validated-optional-advice-without-risking-financial-imports.md), [28](../../initial-release/issues/28-evaluate-up-to-two-local-advice-candidates-before-enablement.md)

## What to deliver

Isolated laptop inference runtime and worker connectivity. Complete the end-to-end behavior below, reusing verified existing work rather than rebuilding it.

## Acceptance criteria

- [ ] Implement the agreed project runtime deployment, pinned model/runtime and
  worker-container connectivity; demonstrate a real local structured response.
- [ ] No production suggestions enabled, no cloud fallback, no interference with
  existing Ollama consumers; record cold load and memory observations.
- [ ] Use a dedicated Docker inference service, as selected by Sourav during planning.
  Resolve candidate/license suitability and resource limits before implementation.
  Any installation/download/service changes require bounded host approval.

## Decision and external gates

D1 deployment choice resolved: dedicated Docker inference service; existing native Ollama remains untouched. Candidate suitability, resource allocation and host-change authorization remain open.
Read the [decision register](../spec.md#decision-register). A resolved decision does not authorize coding or live changes.

## Verification

Real worker-container-to-runtime request on the approved laptop; record pinned versions, cold load, response schema and memory, not service-up alone.

Follow [common completion rules](../spec.md#completion-rules): TDD for changed public behavior, runtime/browser proof, standards and spec review, and separate local/host evidence.

## Current evidence and completion

Not accepted as complete. Local implementation is done; the real laptop GPU
demonstration and host-change approval remain open.

Local evidence:
- Dedicated `compose.inference.yaml` (loopback-only port, pinned image/runtime,
  own volume, GPU reservation, bounded logs) and worker host networking with
  `INFERENCE_URL` plus bounded timeout/attempt controls in `compose.worker.yaml`.
- `worker/advisory.py` client speaks the Ollama generate API, validates JSON
  classification/confidence/explanation and stamps model/prompt version; 9 tests
  cover valid, unavailable, HTTP-error, malformed and invented outputs.
- Candidate shortlist from primary sources: `qwen2.5:7b-instruct` (Apache-2.0)
  and `phi3.5` (MIT). Neither is qualified or downloaded.
- Operator runbook: `docs/runbooks/inference-runtime.md` (prerequisites, pull,
  pin digests, structured smoke, enable, benchmark, rollback).

Required on the deployment laptop before this task can close (user-run, approval
needed for any install/service change):
1. Confirm NVIDIA container GPU access and free disk.
2. Start the service, pull at most two candidates, record digests.
3. Obtain one real structured response from the worker container.
4. Record cold-load time and observed GPU memory.

Implementation commits: `0a8b173`, `17cf8da`.
