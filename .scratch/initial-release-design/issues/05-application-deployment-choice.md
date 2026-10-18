# Application stack and deployment choice

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 01, 03
Parent: [Initial release technical design](../map.md)

## Question

Given host facts and stack evidence, which application/worker languages,
frameworks, development/deployment runtimes, and module interfaces should the
initial release use? Agree a maintainable concrete choice with Sourav, keeping
one mini-PC application and one laptop worker. Establish normal local developer
workflow without choosing sample-dependent parser behavior.

User deployment constraint: project application, worker and database run in
Docker containers. Native deployment is exceptional and only when very simple;
discuss any proposed exception before selecting it. Verify GPU access for a
containerized worker/model path rather than assuming native Ollama proves it.

## Resolution evidence

An agreed stack and deployment layout, rejected alternatives and reasons where
material, and any host prerequisites still needed before real deployment.

## Evidence to consult

[Host inventory](../research/host-storage-wake-inventory.md) records concrete
mini-PC resources and runtimes, including two apparent Docker daemons and
limited root-disk headroom. Establish the intended daemon/socket; do not modify
existing application/database containers or assume that Node's absence from one
PATH rules out a containerized web stack.

## Discussion history

The initial round proposed backend/worker language and UI interaction choices;
the resolution below supersedes this candidate discussion.
Candidate remains Django/Python with custom server-rendered responsive pages,
small browser JavaScript and Chart.js, not a selected stack. Read-only local
Docker and mini-PC daemon evidence is being checked before developer/deployment
workflow defaults are proposed. Storage remains as accepted in ADR0001.

The [container workflow snapshot](../research/container-workflow-facts.md)
finds no local Docker client in checked Mac locations and verifies two live
mini-PC Docker daemon processes. Current default CLI reaches the snap-root
server. Developer runtime setup and an explicit production endpoint are
prerequisites, not permission to modify existing services.

## Answer

Sourav accepted Q37-Q38 and clarified Q39: Django application, Python laptop
worker, custom responsive server-rendered pages, small JavaScript modules and
Chart.js. No separate React application initially. Worker job/results use the
application API, never direct PostgreSQL. Project deployment stays Docker-first
under the established guardrails and storage ADR.

Development is on the Mac, with as much suitable local testing as possible.
At meaningful milestones, run full end-to-end checks on the actual deployment
hosts. This does not select isolated local Docker Compose, permit native database
installation, or make real-host tests a substitute for local behavioral tests.
Exact local runtime/tool setup is an explicit prerequisite for implementation;
do not infer it from this answer.

See [stack ADR](../../../docs/adr/0002-python-application-and-rendered-ui.md).
The container-workflow evidence remains applicable: local Docker CLI was not
found, mini-PC has two live daemons, and production must choose an explicit
endpoint without changing unrelated services. Final framework/runtime versions,
image pins, paths and secrets will be prepared and verified before deployment.

Detailed UI interactions, authentication/transport, public test interfaces,
job recovery and GPU/container integration remain their own decision tickets.
This resolves the stack and developer-host strategy, not those dependent details.
No installation, implementation, target change, commit or push performed.
