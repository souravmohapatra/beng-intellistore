# Domain docs

## Before exploring or changing the project

- Read root `GLOSSARY.md` when present.
- Read relevant decisions in `docs/adr/`.
- While the standalone glossary is absent, use the HLD's glossary and financial
  reporting definitions as the existing domain vocabulary.
- If glossary or ADR files are absent, proceed without scaffolding empty files.

## Layout

Use a single-context layout:

- `GLOSSARY.md`: canonical domain terms and meanings.
- `docs/adr/NNNN-<decision>.md`: consequential architectural decisions.

## Consumer rules

- Use the glossary's terminology in specs, tickets, interfaces, and tests.
- Surface conflicts with existing ADRs before proposing a different design.
- Keep implementation decisions out of the glossary.
- Create or update glossary entries when terminology is resolved. When moving
  definitions out of the HLD, replace them there with a pointer so the root
  glossary becomes the single source of truth.
- Record an ADR when a real trade-off produces a decision that is costly to
  reverse and would be surprising without its rationale.
- Keep specs, glossary entries, and ADRs authoritative for their own concerns;
  link rather than duplicate their contents.
