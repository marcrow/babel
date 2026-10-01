# Entries are identified by content signature, not by path

An entry's identity is the MD5 of its content. A path is a property of the
machine rather than of the wordlist, so identifying entries by path would mean
re-qualifying ~1,200 wordlists every time the catalog meets a new environment.

This is what lets `catalogue.jsonl` be committed and shared carrying no
absolute path at all: a new machine runs the scan, rebuilds its bindings by
signature, and inherits the qualification work for nothing.

## Considered Options

**Hashing a prefix of the file** — the cheap option, and unsafe precisely here.
SecLists ships wordlists that are prefixes of one another
(`subdomains-top1million-5000` / `-20000` / `-110000`, `raft-small` / `-medium`
/ `-large`). A prefix hash would collapse exactly the wordlists whose
difference drives the choice.

**Hashing the filename** fails on rename and collides across collections, which
hold several `common.txt`.

**Full-content MD5** over the ~2.2 GB installed costs on the order of ten
seconds, in an operation that runs rarely, and it is folded into the scan's
single pass over each file. There is nothing to optimise.

## Consequences

Identical content at two paths is one entry with two bindings, so duplicates
such as `xato-net-10-million-usernames.txt` and its `-dup.txt` collapse on
their own.

A wordlist updated upstream changes signature, and would otherwise read as one
entry gone plus one entry new — silently losing its intent. The scan detects
this case (same path, same name, new signature) and offers to carry the intent
forward.

MD5 is used here as an identifier, not as a security primitive. Collision
resistance is not a requirement.
