---
name: wordlists
description: Pick fuzzing wordlists from the local catalog. Use whenever a mission needs a wordlist — directory, file, extension, parameter, API route, subdomain, vhost, username, password or injection-payload fuzzing — and before reaching for a remembered SecLists path.
---

# Wordlist selection

`local.jsonl` describes every wordlist installed on this machine, one JSON
object per line. **Never read it whole.** Grep it: one entry per line means a
match costs you one line.

A path you remember is not evidence the file is here, and a filename is not
evidence of what the file contains. Query the catalog.

## Entry shape

```json
{"sig":"8f14e45fceea167a5a36dedd4bea2543","name":"raft-large-directories.txt",
 "collection":"seclists","category":"Discovery/Web-Content","intent_from":"model",
 "intent":"Directory names harvested from the RAFT
 research corpus; a hit is a real directory on the server, not a guessable
 word.","target":["directory"],"tech":["generic"],"provenance":["curated"],
 "shape":["bare-word"],"language":["generic"],"order":"alphabetical",
 "case":"lower","lines":62284,"bytes":732119,"freshness":"2011",
 "paths":["/usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt"]}
```

`intent: "TODO"` means scanned but not yet qualified. Say so rather than
guessing from the name.

`intent_from` says who wrote the intent: `harvested` from the collection's own
documentation, `model` from a qualification run, `hand` from the operator. Trust
them in that order when two entries disagree; the axes come from a model either
way.

An entry carrying `kind` is **not a wordlist**: `payload-file` is delivered or
uploaded whole, `source-code` is compiled or run, `structured-data` must be
parsed first, `binary` is compressed or not text. No `kind` means it is a
wordlist. One grep lists every exception on the machine:

```sh
rg '"kind"' $C | jq -r '[.kind,.name,.intent]|@tsv'
```

A grouped entry carries `files` instead of `lines`, and its `paths` point at a
directory: `Fuzzing/User-Agents` is 4,499 files and one concept.

## Querying

```sh
C=local.jsonl

# start from what you are enumerating
rg '"target":\[[^]]*"api-route"' $C

# then narrow
rg '"target":\[[^]]*"directory"' $C | rg '"tech":\[[^]]*"iis"'

# free text across intents
rg -i 'coldfusion|struts' $C

# readable shortlist, smallest first
rg -i 'subdomain' $C | jq -r '[.lines,.name,.intent]|@tsv' | sort -n | head -20

# the exact path, once chosen
rg '"name":"raft-large-directories.txt"' $C | jq -r '.paths[0]'
```

## Choosing

1. **target first.** It is the axis that eliminates most candidates. "HTTP
   fuzzing" is not a target; `parameter` and `directory` are different jobs.
2. **tech**, when you know it. Prefer a `generic` list over a wrong-tech one.
3. **shape** — check it against your tool. A `bare-word` list used for file
   discovery needs extensions appended; a `rooted-path` list already carries
   its leading `/` and will double it under `ffuf`.
4. **order** before you truncate. `head -n` on a `frequency` list is a
   strategy; on an `alphabetical` list it just discards most of the alphabet.
   `suspected-frequency` was inferred, not proven — treat it as a hint.
5. **case** against the target: a `lower` list misses mixed-case paths on
   Linux, which matters less on IIS.
6. **lines** against your request budget. Start small and escalate; a 9.5M-line
   list is a decision, not a default.
7. **freshness** — a 2015 subdomain list cannot know a service invented after
   2015.

Return two to five candidates with path, line count, and one sentence each on
why. If you need to compare overlapping candidates, sample and compare them
yourself: the catalog records no relationship between wordlists.

## Combining

The catalog states no combinations, because the axes imply them: a
`shape: bare-word` list aimed at `target: file` needs an `target: extension`
list alongside it. Derive the pairing, do not look it up.

## Limits

- Only installed wordlists are described. Absent from the catalog means absent
  from the disk, not absent from the world.
- The catalog carries no warnings. Whether a password list will lock accounts,
  or a payload is destructive, is your judgement to make, not the catalog's.
- If the catalog is wrong, say which entry and why. Intents are hand-correctable
  and corrections are the point.
