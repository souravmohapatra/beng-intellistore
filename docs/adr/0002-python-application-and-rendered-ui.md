# Use Django and Python with a custom server-rendered UI

Use Django for the web application, Python for the laptop worker, and custom
responsive Django-rendered pages with small JavaScript modules and Chart.js.
This keeps authentication, authoritative data handling and statement processing
in a Python-centered stack without a separate React application initially;
charts and status updates may update without full-page reloads. The worker uses
the application's job/result API rather than direct PostgreSQL access.

## Development and validation

Develop on the Mac and run as many appropriate tests there as possible, followed
by full end-to-end checks in the actual deployment environment at meaningful
milestones. Project deployment remains Docker-based. Sourav selected Docker
Desktop as the Mac development/test runtime for isolated PostgreSQL and file
storage; it was installed and verified on 2026-10-21 (Docker 29.9.1, Compose
v5.6.0) with pinned dependencies. Local success does not establish GPU, wake,
storage, backup/recovery, or real-host deployment acceptance.
