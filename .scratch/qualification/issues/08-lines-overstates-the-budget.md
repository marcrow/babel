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

**Status:** done

- [x] An entry records how many of its lines are requestable, distinct from how
      many lines it has.
- [x] Blank lines count as unrequestable too.
- [x] A comment is recognised by the convention each collection actually uses,
      found by looking rather than assumed; `#` is the one the test found.
- [x] The selection skill tells an agent to budget on the requestable count, and
      to strip comments before use.
- [x] The scan's self-check covers a file that is half comments.

## Comments

`requestable` on every file entry, counted in the pass the scan already makes.
170 of the 1,372 file entries carry fewer requestable lines than lines; 2,532
unrequestable lines in all, and `cms-configuration-files.txt` reads 16 -> 10 as
the ticket predicted.

The comment convention was looked for rather than assumed, across every
installed file: `;`, `//` and `--` are **not** comments here. They appear as
themselves in the metacharacter and SQLi lists -- `; execute immediate ...`,
`//`, `-- -` are payloads -- and stripping them would have deleted content from
34 to 52 entries each.

`#` alone is not the convention either. A bare `#` prefix is content: 13,107 of
`walk-the-line.txt`'s passwords start with one, and the Dutch lists are full of
hashtags. The rule is `#` repeated then whitespace or end of line, which takes
`# Drupal`, `## WordPress` and a `######` separator while leaving `#1qaz` and
`#aalst` requestable. That distinction is what the self-check pins.

Nor is `<!--`, which was the next candidate: `SSI-Injection-Jhaddix.txt` is 71 of
its 75 lines starting with `<!--`, and those lines are the payloads. The one real
XML header found, the `<!-- from: http://h4k.in/... -->` block in
`XSS-EnDe-h4k.xml`, costs 2 lines of 1,287 in a file that has to be parsed before
it is fuzzed at all. Indented comments are the same story: 29 lines across four
entries, every one of them `source-code`, so no rule for them either -- a leading
space is cheaper to leave requestable than to risk against a payload.

Grouped entries are untouched: they carry `files` and never had a line count to
overstate.

The strip recipe in the skill was checked against the count rather than assumed:
it reproduces `requestable` on all 144 affected entries under 200k lines. It
needs `grep -a`, because `MSSQL-Enumeration.fuzzdb.txt` and
`multiplesources-passwords-fabian-fingerle.de.txt` each carry a stray non-text
byte, and grep otherwise declares the file binary and drops lines in silence --
63 of them, from a wordlist an operator would believe was merely decommented.
