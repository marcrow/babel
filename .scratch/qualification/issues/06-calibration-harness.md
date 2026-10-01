# 06: Measure which model is good enough, per category

**What to build:** the operator decides which model to trust on the basis of a
measurement rather than an assumption, before committing to the full run. The
output is a routing decision per category, which 02 already knows how to read.

Two lots of roughly thirty entries. One drawn from the entries that already
have human-written documentation, which serves as the arbiter and is hidden
from the model. One drawn from the undocumented and deliberately hard
categories — injection payloads, pattern matching — plus the Burp payload
lists as a weakly-memorised probe, because the famous corpus is in every
model's training data.

Each lot runs in two conditions: with the path and filename, and without.
**The gap between the two conditions is the result.** A model that scores only
when it can see the path is reciting a memorised corpus, and will fail on the
overwhelming majority of entries, which are obscure.

A split answer is the expected answer: recognising subdomain or username lists
from a sample is easy, telling an injection payload from legitimate template
syntax is not. "Cheap model everywhere except the payload categories" is a
successful measurement, not a failed one.

This is a throwaway script. It runs once to produce a decision and is then dead
code, so it carries no tests — decided in the spec.

**Blocked by:** 02.

**Status:** ready-for-human

- [ ] Both lots are drawn reproducibly, and the hard lot is deliberately
      weighted toward the categories where failure is expected.
- [ ] Every model sees only what it would see in production; the arbiter's text
      is never shown to the model being measured.
- [ ] Each lot is run in both conditions and the per-condition scores are
      reported separately, never averaged into one number.
- [ ] Results are broken down per category, not per model only.
- [ ] A small number of the hardest cases are escalated to the strongest model
      so the operator arbitrates thirty entries rather than thirteen hundred.
- [ ] The outcome is written as the category-to-model routing that 02 consumes.

## Comments

`calibrate.py` is written: both lots drawn reproducibly from a fixed seed (30
documented, 20 hard plus 10 Burp `.pay` probes), each lot run in both conditions
against both models, the documented lot scored against README text the model
never saw, the hard lot judged cheap against strong blind and order-flipped,
results reported per category and per condition and never averaged, six
escalations printed for the operator, and the outcome written to `routing.yml`,
which `qualify.py` prefers over `config.yml`.

Only the draw has been exercised. Running it needs `ANTHROPIC_API_KEY` and costs
money, so it is the operator's to run. No tests, by the decision in the spec.
