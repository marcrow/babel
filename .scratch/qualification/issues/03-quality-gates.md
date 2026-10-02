# 03: Refuse a run that produces interchangeable intents

**What to build:** the failure that actually happened in public — a catalog of
2,285 entries carrying 43 distinct summaries — is caught by a number rather
than by the operator reading 1,379 sentences. A run whose intents are too
repetitive, or that leans on filler vocabulary, fails loudly and changes
nothing.

**Blocked by:** 01.

**Status:** done

- [x] Distinct intents divided by entry count is computed and reported on every
      run.
- [x] A run below the agreed ratio exits non-zero and writes nothing at all;
      a partially bad run never becomes the catalog.
- [x] An intent containing banned filler vocabulary is rejected; that entry
      stays `TODO` and is named in the report.
- [x] The banned vocabulary is data, editable without touching logic.
- [x] The self-check covers both gates with a fake model that returns the same
      sentence every time, and with one that returns filler.

## Comments

Both gates apply to **every** intent that would reach the catalog, whoever wrote
it. Harvesting human text is not an exemption: the first harvest pass shipped 24
byte-identical intents, because the `raft-*` README documents a family of 24
wordlists in one sentence, and that is the `ronin-wordlists` failure arriving by
another door. A sentence claimed by more than one entry is now no intent for any
of them and they fall through to the model.

Distinctness is measured over every intent the catalog would then carry, divided
by the entries carrying one — not over the run. Resumability turns one pass into
many small runs, and a per-run measure cannot see repetition across them. Below
the `distinctness` threshold in `taxonomy.yml` (0.95) `qualify` returns no deltas
at all, so the caller has nothing to write and exits non-zero.

Banned vocabulary and the minimum intent length are both data in `taxonomy.yml`,
matched on word boundaries, and reject the entry rather than the run. Confirmed
with a stubbed model returning one sentence for every entry, in a copy of the
tree under a scratch directory: distinctness 0.04, nothing written, exit
non-zero. A year a README states survives even when the sentence around it is
rejected, because the year is a fact about the entry and the sentence was not.

**The banned list was tuned on evidence, twice.** `common` as a bare word
rejected "the 500 most common passwords in the 2021 breach"; it is now the filler
phrases `common terms`, `common words`, `common names`, `commonly used`.
`wordlist` as a bare word rejected "a ZIP archive holding one text wordlist of
23,000 Dutch words"; it is now the tautological openers `a wordlist of`,
`this wordlist`, `wordlist containing`, `wordlist for`. The spec's own example,
"a wordlist of common terms", is still refused twice over. `list of` stays banned
as the spec asks, at a measured cost of roughly one entry in forty, which a
rerun usually rephrases.
