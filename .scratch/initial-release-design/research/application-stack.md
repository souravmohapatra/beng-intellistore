# Application and worker stack evidence

Date: 2026-10-18. Status: research, not a selected stack or ADR.

## Candidate recommendation

Prefer **Django with server-rendered pages, modest browser JavaScript, and a
Python worker**, subject to the deployment investigation and Sourav's decision.
This recommendation is an architectural inference: the initial UI requires
charts, forms, review, and search, while authoritative financial behavior belongs
on the server. Django supplies database modeling, authentication, and behavioral
test tools together. A TypeScript web application remains reasonable if richer
client interaction becomes a concrete priority; it does not improve the source
extraction problem by itself.

No claim here establishes the two-second response target, NAS deployment
compatibility, or GPU/model fit. Documentation versions cited are evidence for
capabilities, not proposed dependency pins.

## The two practical options

| Concern | Python application and worker | TypeScript application and Python worker |
| --- | --- | --- |
| Application | Django, templates, small JavaScript modules | Next.js/React application with server endpoints |
| Persistence candidate | Django ORM with PostgreSQL | Prisma with PostgreSQL |
| Browser chart | Chart.js, no framework wrapper needed | Chart.js inside an interactive client component |
| Human authentication | Django's built-in session/login facilities | An authentication/session library selected explicitly |
| Worker | Python process calling application job/result endpoints | The same Python worker and HTTP ownership boundary |
| Operational implication | Python production application and worker; browser JavaScript | Node.js application plus Python worker; two server-language toolchains |

This is not an exhaustive dependency list. Both need deployment supervision,
database connectivity, secret handling, and application-specific validation.
Neither requires a separate queue or search service merely to express this
design.

## Extraction and exact financial values

Both options retain Python extraction. The standard-library `csv` reader
returns strings unless numeric conversion is requested, permitting explicit
format-specific validation before arithmetic. Avoid `QUOTE_NONNUMERIC`, which
converts fields to floats. Plain-text inputs can likewise use known layouts;
automatic format detection is not a requirement. [Python CSV documentation](https://docs.python.org/3/library/csv.html)

`pypdf` documents text extraction, including layout extraction, but explains
that PDFs lack semantic table structure: rows and columns can be positioned
text. Consequently, selectable text is not proof of transaction fidelity.
Treat it as a candidate extractor, not a parser for all four providers; choose
and test the actual extraction method after receiving representative samples.
[pypdf extraction documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)

Python `Decimal` supports decimal arithmetic; construct monetary values from
validated strings rather than binary floats. Django provides `DecimalField`;
Prisma exposes decimal values through its Decimal type. PostgreSQL `numeric`
is exact, unlike its floating-point types. Neither stack forces binary-float
storage. [Python Decimal](https://docs.python.org/3/library/decimal.html),
[Django fields](https://docs.djangoproject.com/en/5.2/ref/models/fields/#decimalfield),
[Prisma types](https://www.prisma.io/docs/orm/v7/prisma-client/special-fields-and-types),
[PostgreSQL numeric types](https://www.postgresql.org/docs/current/datatype-numeric.html)

Proposed boundary rule: serialize money as decimal strings with explicit
currency and validate it on receipt. Compute authoritative aggregates on the
server; browser numbers used to position chart points must not become the
financial source of truth. Final precision, rounding, and balance conventions
remain sample-dependent decisions.

## Authentication, UI, and job APIs

Django supplies users, password handling, login facilities, and permissions.
For one user, provision one account without adding public registration. Next.js
supports application endpoints through Route Handlers; its authentication guide
recommends using authentication libraries rather than treating its educational
examples as a complete secure solution. Worker credentials and authorization
remain separate from a human browser session in either design.
[Django authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/),
[Next.js authentication](https://nextjs.org/docs/app/guides/authentication),
[Next.js Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers)

Chart.js can render line charts directly in browser JavaScript, so the net-cash
graph alone does not justify React. Its canvas content requires deliberate
accessibility support; provide a meaningful textual summary/table, including
coverage and provisional states. The same requirement applies to either UI.
[Chart.js usage](https://www.chartjs.org/docs/latest/getting-started/usage.html),
[Chart.js accessibility](https://www.chartjs.org/docs/latest/general/accessibility.html)

For durable jobs, PostgreSQL row locks and `SKIP LOCKED` support queue-like
consumers. That is a building block, not a complete job system: application
contracts must still define claims, expiry, attempts, stale-result rejection,
idempotency, and publication transactions. Only the application accesses the
authoritative database; the worker uses its API. Django and Prisma document
database transaction mechanisms, but a transaction alone cannot atomically
commit an ordinary NAS file write. Acceptance recovery needs its own design.
[PostgreSQL locking](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE),
[Django transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/),
[Prisma transactions](https://www.prisma.io/docs/orm/fundamentals/transactions)

## Public behavior testing and decision gates

Django's test client exercises requests, authentication, and responses;
database-aware test cases support persistence checks. Playwright's retrying
browser assertions can verify upload/status, dashboard periods, review, and
source access against either application. Prefer observable API/browser outcomes
over assertions about internal module calls. [Django testing tools](https://docs.djangoproject.com/en/5.2/topics/testing/tools/),
[Playwright assertions](https://playwright.dev/docs/test-assertions)

Whichever option wins, tests must cover exact totals, duplicate effects,
correction precedence, stale results, and interrupted processing against the
selected database. Browser tests complement those checks. Framework test tools
do not prove crash durability or real-host performance.

Before selection, establish OS/runtime deployment constraints and the desired
interaction complexity. Before implementation, obtain the four sample formats
and independent expected results. Before release, verify storage failure,
restore, wake/readiness, and the performance envelope on actual hosts.

No installs, implementation, host contact, benchmarks, model selection, or Git
mutations were performed. PostgreSQL hosting is permitted by the user but its
concrete NAS deployment and storage configuration remain unverified.
