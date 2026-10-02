# 08: `lines` overstates the request budget

**What to build:** an entry's line count tells an agent what it will spend, so it
must count what will actually be requested. Today it counts every line in the
file, comments included.

Found by the end-to-end test in 07, which chose `cms-configuration-files.txt` on
the strength of its 16 lines being the best value per request on the machine. The
file holds 16 lines and **six of them are `#` comments**: ten paths, not sixteen,
and an agent that feeds the file to `ffuf` unfiltered spends six requests on
`# Drupal` and `# WorpPress`. 41 entries have samples that are more than a tenth
comment lines.

The scan already reads every line of every file once, so this is a count it can
take for nothing. It is a mechanical fact and no model is to be asked for it.

**Blocked by:** None.

**Status:** ready-for-agent

- [ ] An entry records how many of its lines are requestable, distinct from how
      many lines it has.
- [ ] Blank lines count as unrequestable too.
- [ ] A comment is recognised by the convention each collection actually uses,
      found by looking rather than assumed; `#` is the one the test found.
- [ ] The selection skill tells an agent to budget on the requestable count, and
      to strip comments before use.
- [ ] The scan's self-check covers a file that is half comments.
