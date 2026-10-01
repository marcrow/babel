# Spec: qualification of catalog entries

Status: ready-for-agent
Depends on: the scan (`babel.py`), which already produces 1,379 entries.

## Problem Statement

An agent on a mission has 1,379 wordlists installed and no way to tell what any
of them is for. Today every entry in the catalog reads `intent: "TODO"`, so the
agent falls back on what it does now: recalling a SecLists path from memory,
guessing from a filename, and never discovering the 52 Burp payload lists or
the 1.6M-line sqlmap list sitting on the same disk.

The information does not exist anywhere to be copied. Across SecLists, 120 of
6,002 wordlist files are named in any README. The one public project with the
right schema, `ronin-wordlists`, carries 43 distinct summaries across 2,285
entries. Writing those intents is the whole of this project's value, and a
qualification pass that produces interchangeable sentences reproduces
`ronin-wordlists` at greater cost.

## Solution

A qualification pass that reads each entry's sample and writes its intent and
its axes into `catalogue.jsonl`, preceded by a calibration that measures,
rather than assumes, which model is good enough for which category.

The operator runs the calibration once. It reports, per category, whether the
cheap model's intents hold up against human-written ground truth. The
qualification pass then routes each category to the model the calibration
chose, and refuses to finish if its own output is too repetitive to be useful.

Intents are written once and corrected by hand thereafter. Nothing regenerates
them behind the operator's back.

## User Stories

1. As an agent on a mission, I want each entry to state what it is for, so that
   I can choose a wordlist without recalling a path from memory.
2. As an agent on a mission, I want an intent that says what a hit means, so
   that I can tell a directory list from a list of words that look like
   directories.
3. As an agent on a mission, I want to find wordlists by what I am enumerating,
   so that "fuzzing parameters" and "fuzzing directories" lead me to different
   candidates.
4. As an agent on a mission, I want entries tagged by technology, so that I can
   prefer a Tomcat list over a generic one against Tomcat.
5. As an agent on a mission, I want the shape of an entry's contents recorded,
   so that I know whether a list needs extensions appended before use.
6. As an agent on a mission, I want to know a wordlist's ordering, so that I
   know whether truncating it is a strategy or a mistake.
7. As an agent on a mission, I want provenance recorded, so that I can prefer a
   list derived from real-world data when guessing is failing.
8. As an agent on a mission, I want the natural language of a list recorded, so
   that I do not fuzz a French target with a Dutch wordlist.
9. As an agent on a mission, I want freshness recorded, so that I do not expect
   a 2015 subdomain list to know a service invented in 2020.
10. As an agent on a mission, I want unqualified entries to say `TODO` plainly,
    so that I report the gap instead of inventing an intent from the filename.
11. As an agent on a mission, I want the Burp payload lists and tool-shipped
    lists qualified like any other, so that I discover resources I would never
    have looked for.
12. As the operator, I want to know which model is good enough before I spend
    on the full run, so that I am not choosing between cost and quality blind.
13. As the operator, I want the cheap model measured against human-written
    README text, so that the measurement has an arbiter that is not me.
14. As the operator, I want each model judged both with and without the path
    and filename, so that I can see whether it is reading the sample or
    reciting a memorised corpus.
15. As the operator, I want weakly-memorised wordlists included in the
    measurement, so that the contamination estimate is not taken entirely from
    the most famous corpus on GitHub.
16. As the operator, I want the measurement to cover deliberately hard
    categories, so that I learn where the cheap model breaks rather than
    averaging the failure away.
17. As the operator, I want the result expressed per category, so that I can
    route cheap categories to the cheap model and hard ones elsewhere.
18. As the operator, I want to arbitrate only a small sample by hand, so that
    judging costs me an evening and not a week.
19. As the operator, I want the models shown only what they would see in
    production, so that the measurement predicts the real run.
20. As the operator, I want a mechanical measure of how repetitive the intents
    are, so that the `ronin-wordlists` failure is caught by a number rather
    than by reading 1,379 sentences.
21. As the operator, I want the qualification to fail loudly when that measure
    drops, so that a bad run does not quietly become the catalog.
22. As the operator, I want generic filler vocabulary rejected outright, so
    that "a wordlist of common terms" never reaches the catalog.
23. As the operator, I want axis values validated against a controlled
    vocabulary, so that `PHP` and `php` cannot split one technology into two.
24. As the operator, I want to add a target or a technology by editing one
    file, so that a gap discovered in six months costs a line.
25. As the operator, I want an unknown axis value rejected rather than
    recorded, so that the vocabulary stays enforced instead of merely agreed.
26. As the operator, I want to see how many entries carry each axis value, so
    that I can spot a value that is a synonym of another or that nothing uses.
27. As the operator, I want free existing descriptions harvested before any
    model runs, so that I do not pay to rewrite, worse, what a human already
    wrote.
28. As the operator, I want to know which intents came from a README and which
    from a model, so that I know how much to trust each.
29. As the operator, I want to correct a wrong intent by editing a line, so
    that fixing the catalog never requires running anything.
30. As the operator, I want my corrections to survive the next qualification
    run, so that the same mistake is not rewritten over my fix.
31. As the operator, I want to requalify a single entry on demand, so that one
    bad intent does not mean rerunning the batch.
32. As the operator, I want the run resumable, so that an interrupted pass over
    1,379 entries does not start again from zero.
33. As the operator, I want progress reported as it goes, so that I can tell a
    long run from a stuck one.
34. As the operator, I want the token cost estimated before the run starts, so
    that I decide to spend rather than discover the spend.
35. As the operator, I want newly ingested wordlists qualified without touching
    the existing ones, so that adding a collection costs only that collection.
36. As the operator, I want qualification work keyed to the signature, so that
    it survives a path change and a move to another machine.
37. As the operator, I want `catalogue.jsonl` to carry no absolute path, so
    that I can publish it without publishing my filesystem layout.
38. As the operator, I want the grouped entries qualified from a sample of
    their members, so that one concept gets one intent.
39. As a reader of the repository, I want to see which entries remain
    unqualified, so that I know the catalog's coverage without reading it.

## Implementation Decisions

**One seam.** `qualify(samples, taxonomy, ask) -> (entries, report)` is the only
new interface, and the only thing tested. `ask` is the model-calling function,
injected by the caller, so tests pass a fake and make no network call. Batch
splitting, validation, distinctness, README precedence and merge all sit behind
it. Everything else is a thin caller.

**Routing is data, not code.** The calibration writes which model handles which
category; `qualify` reads it. Changing the routing never means editing logic.

**Three passes, in order.** Mechanical facts come from the scan and are never
asked of a model. Free text is harvested next: the 36 `Use for:` entries, the
per-directory READMEs, the trickest provenance prose. Only entries still
uncovered reach a model. A harvested intent is marked as such and is never
overwritten by a model.

**Hand corrections win.** An intent edited by the operator is marked and treated
exactly like a harvested one: later runs leave it alone. This is what makes
ADR 0001's hand-editable catalog real rather than nominal.

**The controlled vocabulary lives in `taxonomy.yml`**, one list of canonical
values per axis plus aliases. Validation rejects an unknown value rather than
recording it; a rejected entry stays `TODO` and is reported. Adding a value is
a line in that file. YAML, consistent with `config.yml`, read with PyYAML.

**Two quality gates, both mechanical.** Distinct intents divided by entry count
must reach 0.95 (`ronin-wordlists` scores 0.019). A banned-vocabulary list
rejects filler: `wordlist`, `list of`, `common`, `various`, `used for fuzzing`.
A failing entry stays `TODO`; a failing run exits non-zero and writes nothing.

**The prompt shows production inputs only.** Sample as the scan took it — 30
head, 60 reservoir, 10 tail — plus the mechanical axes, which are stated rather
than asked, so the model spends its effort on intent alone.

**Input to the model is `samples.jsonl`; output merges into `catalogue.jsonl`
by signature.** Entries are keyed by signature throughout, per ADR 0002, so
qualification survives a path change and a new machine. No absolute path is
written to `catalogue.jsonl`.

**Resumability is the merge.** Running against a `catalogue.jsonl` that already
holds intents qualifies only what is still `TODO`, which makes resume,
incremental ingestion and single-entry requalification the same code path.

**Calibration is a throwaway script.** Two lots of roughly 30 — one drawn from
the 120 README-documented entries, one from undocumented `Fuzzing/XSS`,
`Fuzzing/LFI`, `Payloads` and `Pattern-Matching`, plus the Burp `.pay` lists as
a weakly-memorised probe. Each lot runs in two conditions, with and without
path and filename. The gap between conditions is the result: a model that only
scores with the path is reciting, and will fail on the 98% that are obscure.
The README text is hidden from the model and used as the arbiter.

## Testing Decisions

A good test here asserts on what `qualify` returns, never on how it got there.
No test calls a model: `ask` is injected, and the fake returns whatever the
case under test needs, including bad output.

Prior art is `babel.py --selftest`: plain `assert`, no framework, no fixtures,
runnable in under a second. Qualification extends it rather than introducing a
second way to run checks.

What is tested, through the one seam:

- An unknown axis value is rejected and the entry stays `TODO`.
- An alias resolves to its canonical value, so `PHP` and `php7` both land on
  `php`.
- Banned filler vocabulary in an intent is rejected.
- A run whose distinctness falls below the threshold fails and writes nothing.
- A harvested intent is not overwritten by a model's.
- An operator-corrected intent is not overwritten by a model's.
- An entry already qualified is not sent to the model again.
- A grouped entry qualifies from its members' sample.
- Merging is keyed by signature, not by name or path.

Not tested: the calibration script, deliberately. It runs once to produce a
routing decision and is then dead code.

## Out of Scope

Wordlist generation and `cook`, which belong to a separate skill. Downloading
remote wordlists: the catalog describes only what is installed. Relationships
between wordlists, such as subset or union; an agent compares its own shortlist.
Warnings about account lockout or destructive payloads, which are the
mission's judgement and not the catalog's. Harness integration, deferred until
the intents have been corrected against real missions. Any service, daemon or
MCP, excluded by ADR 0001.

## Further Notes

The calibration is likely to return a split answer rather than a single model.
Recognising `Discovery/DNS` or `Usernames` from a sample is easy; telling an
SSTI payload from legitimate template syntax is not. A result of "cheap model
everywhere except Payloads, Fuzzing and Pattern-Matching" should be read as
success, not as a failed measurement.

The distinctness threshold guards against the failure that actually happened in
public: `ronin-wordlists` is not wrong, it is empty. Intents that are merely
accurate are a failure mode this project cannot afford.
