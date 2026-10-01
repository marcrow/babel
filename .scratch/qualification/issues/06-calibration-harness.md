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

The harness itself has not been run. What *has* been run, on the subscription, is
a hand-sized version of its two lots with the cheap model, 26 live calls in all,
and it has already paid for itself three times over:

- **Contamination looks low.** Eight documented entries, named against blind:
  blind recovered `html5sec` in `XSS-Jhaddix.txt`, the Tomcat manager, Spring
  Boot actuators and Oracle from the sample alone. The named condition won
  clearly twice out of eight (`Oracle-EBS`, where the filename carries "EBS").
- **The hard lot did not break it,** against the spec's own expectation. Ten
  blind entries from `Fuzzing/XSS`, `Fuzzing/LFI`, `Payloads`,
  `Pattern-Matching` and the Burp `.pay` probes: ten answers, no rejections, all
  specific. "Cheap model everywhere except the payload categories" is looking
  like the wrong prediction.
- **Two prompt failure modes caught, which would have reached all 1,362
  entries.** Concrete examples in the prompt were copied verbatim — one entry
  was handed the `accepted` example, another the `rejected` one — and entries
  began referring to each other by batch position. The example is now about a
  wordlist that does not exist, cross-references are rejected mechanically, and
  so is any intent that reproduces the example.

What this does not establish, and what the harness is still for: a scored
comparison against the README arbiter, per category, with numbers. The residual
risk is no longer vagueness but **confident embellishment** — a generic `raft-*`
list was described as "refined toward WordPress, Joomla, and Drupal", which
nothing in its sample supports. A mechanical gate cannot see that; only the
scored lot can.

No tests, by the decision in the spec.
