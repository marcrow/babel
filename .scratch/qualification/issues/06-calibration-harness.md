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

**Run.** Two lots of thirty, both conditions, both models, on the subscription.
The outcome is in `routing.yml` and the evidence in `calibration.json`.

```
routing:
  Fuzzing: claude-sonnet-5-5
  Payloads: claude-sonnet-5-5
  default: claude-haiku-4-5-20251001
```

**The documented lot says the models are equivalent, and that neither is
reciting.** Scored against README text neither model ever saw, out of 2:

| | named | blind | gap |
|---|---|---|---|
| haiku | 1.85 (n=26) | 1.86 (n=21) | −0.01 |
| sonnet | 1.89 (n=28) | 1.79 (n=24) | +0.10 |

Hiding the path and the filename costs nothing measurable. The contamination
worry the lot was built for does not show up, and on these categories the cheap
model is not behind the strong one.

**The hard lot says the opposite, and it is the more sensitive instrument.**
With no human text to score against, the strongest model compared cheap and
strong head to head, order-flipped and blind: **the strong model won 19 of 19**
blind comparisons, and 17 of 17 named. Not one tie, not one win for the cheap
model, across `Fuzzing/XSS`, `Fuzzing/LFI`, `Pattern-Matching`, `Payloads/Images`,
`Payloads/Zip-Traversal`, `Payloads/File-Names` and the Burp `.pay` probes.

The two results are not in conflict. The documented lot is easy and the arbiter
is coarse: both models sit at 1.8 of 2, so the instrument has hit its ceiling and
cannot separate them. The head-to-head has no ceiling, and it separates them
clearly on exactly the categories the spec expected to be hard. "Cheap model
everywhere except the payload categories" was the right prediction.

The escalations show what the gap is made of rather than that it exists. On
`pcap-strings.txt` the cheap model blind says the terms were "harvested from
real-world code exposure", which nothing supports, while the strong models both
report the sentinel word `wombat` sitting at the end of the file. The failure is
not vagueness, it is confident embellishment.

**Per-category decisions are aggregated at the top-level category.** Twenty
entries cannot support a decision about `Fuzzing/XSS/human-friendly` and
`/robot-friendly` and `/Polyglots` separately; routing matches by prefix, so one
line covers the family. `Pattern-Matching` lost both of its comparisons but
n=2 — below the four-observation floor — so the rule refused to decide and left
it on the cheap model. Moving it is one line in `routing.yml`.

**Three defects in this harness, which had never been run.** The lot arithmetic
broke whenever the lot was smaller than the Burp probe share. The judge was
called once per entry, ~190 sequential calls to the strongest model, now once per
lot for the same information. And the judge's reply parser was strict, so when
the judge changed its formatting between calls the parse returned nothing *in
silence* and deleted an entire condition from the measurement — the first run
reported a 2.00-against-1.23 named/blind gap for the strong model that was pure
parse artefact. It now reads loosely, falls back on order, and says so when it
still comes up short. `--rejudge` and `--route-only` re-derive the verdicts and
the decision from intents already paid for.

**What the run also measured, unasked.** Six of twenty entries were refused by
this project's own gates, and five of the six were our fault: a model answering
`order: ["frequency"]` as a list of one, `laravel` and `symfony` missing from the
vocabulary, and `common` banned as a bare word rejecting "the 500 most common
passwords in the 2021 breach". Fixed; the same twenty now pass 20 of 20. Left
unchecked that would have parked three or four hundred entries at `TODO`.

No tests, by the decision in the spec.
