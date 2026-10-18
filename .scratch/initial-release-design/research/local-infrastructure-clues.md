# Local infrastructure clues

Date: 2026-10-18
Scope: read-only local configuration and repository inspection, no host contact.

| Item | Evidence | Limit |
| --- | --- | --- |
| Mini-PC | Explicit local SSH alias for `beng-mini-pc`; effective connection settings obtained with `ssh -G`. | Does not establish reachability, OS, resources, installed services, or mounts. |
| Laptop | Explicit local SSH alias for `beng-laptop`; effective connection settings obtained with `ssh -G`. | Does not establish reachability, GPU/runtime, wake contract, or sleep behavior. |
| NAS | No explicit `beng-nas` SSH alias found; effective hostname remains unchanged. | Does not establish DNS failure or lack of another connection method. |
| Wake/GPU | HLD records user reports of a wake API and RTX 2070 8 GB. | API contract and hardware behavior unverified. |
| Database hosting | Sourav confirms NAS can host a database service. | Runtime, persistent volume, capacity, and access details unverified. |

Sources: local SSH host declarations and filtered `ssh -G` metadata; project
AGENTS.md, HLD v0.2, docs/agents/domain.md, and local workflow notes. No credential
or key material retained. No host connections, wake calls, or infrastructure
changes were performed. This closes preliminary local discovery only, not the
host inventory task.
