# Reflective Practice Frameworks

This prototype uses a small, explicit subset of reflective practice frameworks rather than trying to encode every educational model into the first version.

The candidate frameworks reviewed for the project were:

- Gibbs' Reflective Cycle
- Kolb's Experiential Learning Cycle
- Socratic questioning
- KWL (Know / Want / Learned)
- What / So What / Now What

The key constraint for Sugar Journal integration is that the system should produce one short reflection question at a time, not a multi-step worksheet. Under that constraint:

- `Socratic` works well for procedural and construction-heavy activities because it can surface why a learner made a choice.
- `KWL` fits reading and writing activities where the learner is working with prior knowledge and newly learned material.
- `What / So What / Now What` fits expressive or experience-first activities where description should come before analysis.

`Gibbs` and `Kolb` remain useful research references, but they are heavier frameworks that naturally expand into multi-step reflection. For a bounded Journal prompt, they are better treated as background influences than as the primary v1 routing targets.

This is why the service uses a seeded mapping plus a generic fallback rather than an exhaustive framework taxonomy.
