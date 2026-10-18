# Application and worker stack evidence

Type: research
Label: wayfinder:research
Status: resolved
Blocked by: None
Parent: [Initial release technical design](../map.md)

## Question

Which small established stack options support one web application and one Python-
capable extraction/local-inference worker without adding standalone queue/search
services? Compare at most two practical options: Python application/worker with
a modest browser UI, versus a TypeScript web application with Python worker.
Consult primary documentation for parsing ecosystem, exact financial values,
database access, authentication, job APIs, charts, and behavior-level testing.

## Resolution evidence

Cited findings in `research/application-stack.md`, focusing on maintenance,
dependency/runtime count and testability. No framework popularity claims,
implementation, installs, benchmark claims, or model/hardware compatibility
assumptions. Give a reasoned candidate recommendation, not a selected stack.

## Answer

Resolved 2026-10-18: Primary-source stack comparison complete. A Python-first Django application with modest browser JavaScript and a Python worker is the candidate recommendation, not a selected stack. See the linked note for the two options, extraction limits, financial types, authentication, charts and tests. Host compatibility, desired interactions and final selection remain open in Application stack and deployment choice.

Evidence: [Research findings](../research/application-stack.md). No host checks, installs, implementation, commits, or pushes.
