# 01: Qualify one entry end to end

**What to build:** an entry that arrived from the scan as `intent: "TODO"` comes
out carrying a real intent and a validated set of axes, and an agent finds it by
grepping the local catalog. The model is faked for this ticket, so the whole
spine is exercised without a single network call.

This is the tracer bullet: controlled vocabulary, validation, the qualification
seam, intent provenance, merge by signature, and the agent-visible result.

Three things land with it:

- **The controlled vocabulary** lives in its own file, one canonical list per
  axis plus aliases, so that `PHP`, `php7` and `php` cannot split one technology
  into three. Adding a value is a line.
- **Intent provenance** is recorded on every entry: harvested from existing
  documentation, written by a model, or corrected by hand.
- **Precedence**: a model never overwrites an intent it did not write. This is
  what makes the hand-editable catalog of ADR 0001 real rather than nominal.

Includes the prefactor this needs: catalog load, merge and write are shared by
the scan and the qualification rather than living inside the scan.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] One function is the only new interface, taking the samples, the
      vocabulary and the model-calling function, and returning entries plus a
      report. The model-calling function is injected by the caller.
- [x] Qualification is keyed by signature throughout, per ADR 0002, and writes
      no absolute path into the shared catalog.
- [x] An axis value outside the controlled vocabulary is rejected; the entry
      stays `TODO` and is named in the report.
- [x] An alias resolves to its canonical value.
- [x] A qualified entry appears in the local catalog with its intent, and one
      grep hit still returns one entry's worth of text.
- [x] An entry whose intent was harvested or corrected by hand is not sent to a
      model and is not overwritten by one.
- [x] An entry already qualified is not sent to a model again.
- [x] A grouped entry is qualified from a sample of its members.
- [x] The existing self-check covers all of the above with a fake model, runs in
      under a second, and makes no network call.

## Comments

`qualify(samples, taxonomy, ask) -> (deltas, report)` in `qualify.py` is the only
new interface. `taxonomy.yml` holds the vocabulary, the banned filler, the
distinctness threshold and the minimum intent length, all as data.  `catalog.py`
holds the load, merge and write the scan and the qualification now share, along
with the two projections (`shared`, `local`) that keep paths and samples out of
the committed catalog. The scan records each entry's `category`, its directory
within the source, so an entry can be routed and matched to documentation
without a path.

Intent provenance is `intent_from`: `harvested`, `model` or `hand`. A model never
writes over the first or the last, enforced in `qualify` for intents harvested in
the same run and in `catalog.merge` for intents already in the catalog.

**A second deliberate deviation, measured rather than reasoned.** The checkbox
says an axis value outside the vocabulary leaves the entry at `TODO`. Rehearsed
on live samples, that cost 30% of entries, and five refusals in six were this
project's fault rather than the model's: `laravel` and `symfony` missing from the
vocabulary, a single-valued axis answered as a list of one, `common` banned as a
bare word. Throwing away the sentence — the only thing a model is paid for —
because a category word is missing from our own file is the wrong trade. So an
unknown value is still never recorded, which is what keeps `PHP` and `php` from
splitting one technology in two, but it is reported as a gap and the entry is
kept. Three things remain fatal: no usable intent, a wordlist with nothing to
enumerate, and a claim of not being a wordlist that the sample contradicts.
Coverage went 81% → 90% → 95% → 98% on one fixed sample, and 95% and 100% on two
samples never seen before.

**One deliberate deviation from the checkbox above.** An entry whose intent is
`harvested` or `hand` *is* sent to a model, for the axes it is missing and never
for its intent, which is neither shown to the model nor replaceable by it. The
ticket's wording would have left 63 entries carrying an intent and no `target`,
which is the axis the selection skill queries first, so they would have been
invisible to the query path that user story 3 exists for. The census made that
gap visible and this closes it. Documented facts still outrank inferred ones: a
year stated by a README beats a year a model guessed.

`babel.py --selftest` runs both self-checks in 0.12s with a faked model and no
network call.
