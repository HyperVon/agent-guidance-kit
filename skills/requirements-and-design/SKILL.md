---
name: requirements-and-design
description: >-
  Clarify desired behavior and select a design approach before implementation,
  starting from an unclear outcome. Use when defining requirements, constraints,
  acceptance criteria, or choosing how to build something. Do not use to evaluate
  an existing system or design (use architecture-review); this skill starts before
  a design exists, it does not judge one that already does.
---

# Requirements and Design

## Authority and boundary

This skill helps define **what to build and how to approach it** when the desired
outcome is not yet clear. It is the upstream sibling of `architecture-review`:

| Skill | Starting point | What it does |
| :--- | :--- | :--- |
| **requirements-and-design** | An unclear desired outcome | Clarifies behavior, identifies constraints, defines acceptance criteria, selects an approach |
| **architecture-review** | An existing system or design | Evaluates it and compares Keep / Evolve / Replace / Greenfield options |

Use this skill before implementation. It is not a substitute for
`architecture-review` (which judges an existing design) and it does not do the
implementation or the execution plan (that is `implementation-planning`).

## Workflow

1. **Frame the outcome.** Name the user/business outcome, not the proposed
   mechanism. Reframe solution-shaped requests into the underlying need.
2. **Elicit requirements.**
   - *Functional:* what the system must do.
   - *Non-functional:* performance, security, reliability, usability, compliance.
   - *Constraints:* fixed stack, deadlines, legal, legacy compatibility.
   - *Assumptions:* what is taken as true and should be validated.
3. **Define acceptance criteria.** Each criterion must be testable and tied to the
   outcome, so a later implementation agent knows when "done" is reached.
4. **Consider alternatives.** Enumerate plausible approaches, including doing less
   or nothing, and record why each was or was not chosen. Scale this analysis with
   the change's risk and impact; do not stand up a heavyweight decision process for
   a trivial change.
5. **Recommend an approach.** Select one, state the trade-offs accepted, and list
   any unresolved decisions that block implementation.

## Required output

Return a record with:

- **user/business outcome** — the result that matters, framed in user terms.
- **functional requirements** — behaviors the system must provide.
- **non-functional requirements** — quality attributes it must meet.
- **constraints** — immovable limits on the solution.
- **assumptions** — taken-as-true claims to validate.
- **acceptance criteria** — testable definitions of done.
- **alternatives considered** — options weighed and the reason each was set aside.
- **recommended approach** — the chosen path and its trade-offs.
- **unresolved decisions** — open choices that must be settled before building.

## Scale the rigor

Do not create unnecessary process for trivial changes. Match the depth of this
skill to:

- **risk** — how damaging a wrong choice is;
- **ambiguity** — how unclear the outcome or constraints are;
- **blast radius** — how many systems or users a change touches.

A one-line bug fix needs a sentence of acceptance criteria, not a full alternatives
matrix. A cross-team platform change needs the full record above.

## Hand-off

When the requirements and chosen approach are settled, hand the record to
`implementation-planning` to produce the execution plan. Do not start coding or
redesigning existing architecture within this skill.
