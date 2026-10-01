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

**Two model paths, the subscription by default.** `ask_cli` runs Claude Code
headless (`claude -p`) with no tools, no system prompt of its own and a working
directory outside this repo, so the model sees the qualification prompt and
nothing else, and the run bills against the machine's subscription instead of a
key. `--api` switches to `ask_api` and the metered key. Both go through the seam
from 01 unchanged.

Measured on the subscription, against real entries: `--tools ""` cut the system
prompt from 13.5K to 2.7K tokens a call, and a thinking budget of 1024 (config,
`qualify.thinking`) holds a batch of ten at twenty seconds against ninety
unbudgeted — thinking is what separates a specific intent from an
interchangeable one, so it is budgeted rather than switched off. Six real
`Discovery/DNS` entries qualified in 15 seconds, six distinct intents, each
visibly read from the sample. At that rate the remaining 1,362 are about 45
minutes. A subscription limit reached mid-run raises `Exhausted`, which the run
treats as an interrupt: it keeps the batches already paid for and says to
rerun.
