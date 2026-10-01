# 04: Harvest the documentation that already exists

**What to build:** before paying a model to describe a wordlist, take the
description a human already wrote. Across the installed collections that is a
small but high-quality seam: a few dozen `Use for:` entries, the per-directory
READMEs where they exist, and the provenance prose shipped with the
real-world-derived lists.

A harvested intent is marked as harvested and is protected by the precedence
rule from 01, so no model later rewrites it worse.

**Blocked by:** 01.

**Status:** done

- [x] Existing descriptions are matched to entries by name within their
      collection and recorded with provenance `harvested`.
- [x] The inconsistent formats in the wild are handled without a parser per
      collection: per-file entries, one-sentence directory blurbs, and prose.
- [x] A harvested intent is never sent to a model and never overwritten by one.
- [x] The report states how many entries the harvest covered, so the remaining
      model surface is known before spending.
- [x] Where documentation carries a staleness warning, that warning reaches the
      entry rather than being dropped.

## Comments

One parser over every `README*` in every source: `## <name or glob>` sections,
`Use for:` preferred, prose otherwise, matched to entries by pattern within the
collection and category, most specific section winning, case-insensitively
because the READMEs misspell it.

Ran for real, with no model call and no spend: 44 sections parsed, 63 entries
matched, 17 intents harvested and 46 rejected by the gates from 03 — 24 of them
the `raft-*` family sharing one sentence, the rest leaning on filler such as
`wordlist` or `common`. The rejected entries stay `TODO` and are named in the
report, so the model surface is known before spending. Twenty-two entries carry a
`freshness` year taken from documentation, including the `subdomains-top1million-*`
staleness warning, whose year survives even though the family sentence it sat in
did not.
