# Design Decisions

Captures the *why* behind non-obvious choices. What exists is in `CLAUDE.md`; why it's that way is here.

---

## Baseline team: Indiana Pacers

Arbitrary starting point — no analytical reason. The Pacers were chosen because of a personal connection (first sports card collected as a kid). Any team would work equally well as the anchor; the important thing is that all other teams are eventually expressed relative to a single, fixed reference.

---

## Baseline player: James Johnson

James Johnson was chosen because he sat in the middle of the seniority distribution at the time the model was designed: experienced enough to appear in a large number of games (giving a reliable performance average), but not so senior that he was likely to retire soon and leave the baseline without a sufficient data window. A superstar would introduce noise from double-teams and load management; a fringe player might not accumulate enough court time to anchor the 1.0 reliably.

---

## Storage format: pickle over JSON or SQLite

`Game` and `PlayByPlayEvent` are Python dataclasses with typed fields (tuples, dates, nested lists). Pickle round-trips these back to the exact same types with no deserialization layer — load a file, get a `Game`. JSON would require a schema and manual reconstruction of each type on load; SQLite would require an ORM or hand-written queries. For a project where the data is only ever read by this codebase, pickle's direct class compatibility outweighs its portability cost.

---

## Defence score is inverted (lower = better)

`defence = 0.5` means the opponent scores at *half* the baseline rate while this player is on court — which is *good*. This is the opposite of `attack`, where higher is better. The inversion was chosen so that defence scores read as a multiplier on opponent scoring rate: 0.5× is excellent, 1.0× is neutral, 2.0× is poor. Do not normalise or compare attack and defence scores directly — they are on different scales with different polarities.

---

## Player pairs as plain `tuple[str, str]`

No custom class. A named pair added no behaviour beyond what a two-element tuple provides, and would have required boilerplate (`__eq__`, `__hash__`, ordering) for negligible benefit at this stage. If pair-specific methods become necessary later, promote then.

---

## Cross-team comparison: ratio chains

*(Placeholder — reasoning to be documented.)*

Players on different teams may never share court time, making direct on/off comparison impossible. The current approach links them via weighted chains of ratio comparisons through shared intermediaries. **Why this method was chosen over alternatives (e.g. a global regression, a graph-based PageRank-style score, or simply accepting team-relative scores without unification) has not yet been documented.** Revisit and fill in before Phase 3 begins.
