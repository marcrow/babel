# 02: Qualify real entries against real models

**What to build:** the operator points the qualification at the catalog and it
genuinely qualifies entries, reporting what it will cost before it starts and
how far along it is while it runs. An interrupted run resumes where it stopped
rather than starting over, and which model handles which category is a
configuration value rather than a code change.

Demonstrable on a handful of real entries end to end.

**Blocked by:** 01.

**Status:** done

- [x] The model-calling function is implemented for real and passes through the
      seam built in 01, unchanged.
- [x] Entries are sent in batches, and the model sees only what it would see in
      production: the sample as the scan took it, plus the mechanical axes
      stated rather than asked.
- [x] An estimated token cost is printed before any call is made, and the run
      can be declined at that point.
- [x] Progress is reported as the run proceeds, so a long run is
      distinguishable from a stuck one.
- [x] Interrupting and rerunning qualifies only what is still `TODO`, with no
      duplicated work and no lost intents.
- [x] Requalifying a single named entry works through the same path as a full
      run.
- [x] Which model handles which category is read from configuration, defaulting
      to one model for everything.

## Comments

`ask_api` calls the Messages API over `urllib`, so no dependency was added, and it
passes through the seam from 01 unchanged. Verified end to end against a stubbed
model on 25 real entries, harvested ones among them: the estimate is printed and
declinable before the first call, progress is reported per batch, a rerun makes
zero calls, `--only NAME` requalifies one entry through the same path, and
`routing.yml` sends a category to another model.

`--only` passes no documentation, because requalifying is asking the model and
the harvest already had its turn — otherwise a harvested entry would silently
get the same sentence back. A `hand` intent refuses to be requalified without
`--force`, and `--force` makes the entry surrender its protection in the merge
rather than being quietly ignored. An interrupt keeps the batches already
answered and says to rerun.

The real run needs `ANTHROPIC_API_KEY`, which this environment has not got.
