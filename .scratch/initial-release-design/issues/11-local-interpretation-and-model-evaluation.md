# Local interpretation contract and model evaluation

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 01, 05, 07
Parent: [Initial release technical design](../map.md)

## Question

After host and sample evidence, identify where deterministic rules actually
leave useful interpretation work, define structured advisory output and review
rules, and choose a documented local runtime/model shortlist and evaluation
criteria. Decide acceptable processing time, quality, and unavailable-model
behavior without claiming fit or extraction quality before a real benchmark.

## Resolution evidence

An agreed advisory contract and bounded candidate/evaluation plan. If selecting
a model needs benchmark evidence, create a precise prerequisite task and keep
the choice open; no arbitrary LLM call on fully deterministic imports.

## Confirmed advisory role

Sourav accepted Q67-Q69:

- Limit initial local-model work to suggestions for unresolved financial
  classification (spending/income/transfer/refund/unknown), using extracted rows
  and bounded relevant context. Structured allowed values, source references,
  brief explanation and abstention; explicit user confirmation before effects.
  No model parsing/repair of amounts/dates/balances, categories or chat.
- Optional advisory failure must not discard deterministic validated results.
  Publish those with visible unresolved review/advice-unavailable status; retry
  advice separately/bounded rather than repeat the financial import. This
  refines the earlier general transient-inference retry rule: core processing
  failures keep its three-attempt policy, optional advisory failure degrades.
- Choose exact local runtime/model through a bounded actual-laptop evaluation
  task during implementation, before enabling advice. Compare against rules-only
  baseline on labelled cases; measure correctness, abstention/coverage, latency
  and memory. No cloud fallback or current fit claim. Dataset/threshold/time
  budget are agreed below.

## Confirmed evaluation gates

Sourav accepted Q70-Q72:

Q70 accepted: independently label 50 held-out unresolved/ambiguous classification cases,
including legitimate unknowns. Initial enablement bar: at least 90% correct
non-abstained suggestions and suggestions on at least 50% of cases; report counts
and class-specific failures, not just percentages. Labels precede inference;
do not tune on this hold-out. This is a small pilot, not a reliability guarantee.

Q71 accepted: initial actual-laptop target of 100 unresolved transactions in ten minutes
of warm inference, reporting cold-load time separately; stable fit on existing
8 GB GPU hardware without out-of-memory failures. Bound execution and degrade to
review on failure. Validate this target rather than assert feasibility.

Q72 accepted: evaluate at most two documented local quantized candidates initially; choose
exact versions/runtime/quantization through the implementation evaluation task.
If neither meets the quality/resource/time bar, keep advice disabled and allow
the deterministic application to ship with manual review. No cloud fallback.

## Answer

The advisory contract and bounded evaluation plan are accepted through Q72.
No exact model/runtime/quantization is selected: that choice remains open until
actual-laptop evidence passes the gates above. The deterministic application may
ship with manual review when no candidate passes, so unresolved model selection
does not block specifying or implementing the core application.

Carry this prerequisite into the implementation tickets before enabling advice:

1. Check primary model/runtime documentation and license/compatibility; pin at
   most two local quantized candidates and the tested runtime versions. Existing
   native Ollama is evidence, not authorization to ignore Docker deployment.
2. Establish independently reviewed labels for the 50 held-out cases before
   inference, with legitimate unknowns and varied classifications. Keep real
   financial data outside Git; tune prompts on separate development cases.
3. Report correct/incorrect non-abstained suggestion counts, coverage and
   per-class mistakes, including performance against the rules-only baseline.
   Treat unknown as abstention, not a way to inflate answered-case correctness.
4. Measure the separate 100-item warm workload and cold-load time on the actual
   laptop; record hardware/runtime/context/quantization and observed memory.
   Test malformed output, missing evidence, timeout and out-of-memory handling;
   invalid advice cannot change facts or bypass explicit confirmation.
5. Enable only a candidate passing quality, coverage and resource/time gates;
   otherwise keep advice unavailable/disabled and retain manual review. Record
   the benchmark and limitations. Do not tune on failed hold-out examples and
   then present their rerun as an independent result.

This resolves the design decision, not the benchmark. No model was downloaded,
loaded or run, no GPU access was verified, and no target configuration changed.
Actual timings, memory fit and quality remain untested. Exact timeout/retry
parameters are implementation calibration under the bounded failure contract.
