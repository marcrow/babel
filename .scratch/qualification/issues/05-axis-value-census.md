# 05: Show how the vocabulary is actually used

**What to build:** the operator can see how many entries carry each value of
each axis, so that a value which is a synonym of another, or which nothing
uses, becomes visible. A controlled vocabulary drifts silently otherwise, and
the whole point of enforcing it is to be able to review it.

**Blocked by:** 01.

**Status:** done

- [x] Entry counts per value, per axis, are reported on demand.
- [x] Values defined in the vocabulary that no entry uses are listed.
- [x] Entries carrying no value at all on an axis are counted.

## Comments

`qualify.py --census`: counts per value per axis, values the vocabulary defines
that nothing uses, entries carrying no value on an axis, and any value outside
the vocabulary that predates enforcement. `freshness` is covered too, as an open
axis declared in `taxonomy.yml` — it is a year, so it has no vocabulary and
nothing can fall outside it.

It earned its keep immediately: it is what showed that harvested entries carried
an intent and no `target`, which is why 01 now asks a model for their axes.
