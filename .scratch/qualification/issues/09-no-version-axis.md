# 09: Two wordlists for the same technology, different major versions

**What to build:** a decision, then possibly an axis. The catalog can say an entry
is for Magento. It cannot say which Magento.

Found by the end-to-end test in 07, and named by it as the single biggest unknown
remaining. `sitemap-magento.txt` carries `freshness: 2014`, which is Magento 1,
and `trickest-cms-wordlist/magento.txt` carries 2024, which is probably Magento 2
— and "probably" is the problem. Against a Magento 2 storefront the first list
wastes 16,544 requests on a path layout that no longer exists, and nothing in the
catalog warns of it. The same question waits behind every long-lived technology
here: Tomcat, Joomla, WordPress, ColdFusion.

`freshness` is a proxy and a poor one: a 2024 list may still be describing the old
version, and a 2014 list may be version-agnostic.

The decision to take first is whether this belongs in the catalog at all. An
agent that knows the target's version can read it from the intent, which already
says things like "Magento 1.x path layout" where the sample shows it. An axis is
only worth adding if the intent's prose is not enough to filter on, and that is a
question about how the catalog is queried rather than about what is true.

**Blocked by:** None, but it wants `/domain-modeling` before any code: this is a
new term in the language, not a feature.

**Status:** needs-triage

- [ ] Decide whether version is an axis, a convention inside the intent, or
      nothing.
- [ ] If it is an axis, decide what it holds for the 1,100 entries where version
      is meaningless.
- [ ] Either way, the entries where a major version actually changes the paths
      are identified and say so.
