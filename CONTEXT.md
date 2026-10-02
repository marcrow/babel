# Babel

A catalog describing every wordlist installed on a machine, so that an agent on a
mission can tell what each one is for and choose between them.

## Language

### Core

**Wordlist**:
A file of candidate strings consumed by a fuzzing or bruteforce tool.
_Avoid_: dictionary, word list, worldlist

**Catalog**:
The description of every installed wordlist, written to be read by an agent. It
describes wordlists; it does not contain them.
_Avoid_: index, database, registry

**Entry**:
The unit of the catalog. Describes either a single wordlist or a group of
wordlists treated as one concept — or, marked by its **kind**, an installed file
that is not a wordlist at all: a web shell sits in `Web-Shells` and an agent
searching that directory has to be told not to fuzz with it.
_Avoid_: record, item, row

**Requestable**:
How many of an entry's lines a tool would actually ask the target for: its line
count less the blank lines and the `#` comments. What a mission budgets on,
where **lines** is the file's size rather than its cost.
_Avoid_: usable, effective, net lines

**Collection**:
A set of wordlists with a common origin, installed and versioned as a unit:
SecLists, the Burp payload lists, the lists shipped inside a tool. The directory
it is mounted at is a property of the machine, so renaming that directory does
not rename the collection: an entry whose signature the catalog already knows
keeps the committed name.
_Avoid_: pack, repo, bundle

**Mission**:
An agent's work against an audit environment, for which it must choose
wordlists. The consumer of the catalog.
_Avoid_: task, job, engagement

### Identity and location

**Signature**:
An entry's identity, the MD5 of its content. A path is a property of the
machine, not of the wordlist.
_Avoid_: id, hash, checksum, fingerprint

**Binding**:
The association between a signature and the paths where that wordlist sits on a
given machine. Local, disposable, never edited by hand.
_Avoid_: mapping, link, resolution

**Category**:
An entry's directory within its source, such as `Discovery/Web-Content`. A
property of the collection rather than of the machine, so it is committed: it is
what routes an entry to a model and what matches it to a README.
_Avoid_: folder, group, section

**Source**:
A declared filesystem root holding wordlists, with its exclusion rules. Anything
outside every source does not exist for the catalog.
_Avoid_: root, location, directory

**Installed**:
Present on this machine's disk. The catalog describes only installed wordlists.
_Avoid_: available, local, present

### Operations

**Scan**:
The walk over the sources that establishes mechanical facts and rebuilds the
bindings. It calls no model.
_Avoid_: crawl, sync, discover, index

**Qualification**:
The writing of an entry's intent and axes. The only part of this project that
needs a model, and the only part that carries value.
_Avoid_: enrichment, annotation, tagging

**Intent**:
One or two sentences stating what an entry is for. An intent that could have
been written without opening the file is a failed intent.
_Avoid_: description, summary, purpose, blurb

**Intent provenance**:
Who wrote an entry's intent: `harvested` from documentation a human already
wrote, `model` from a qualification run, `hand` from the operator correcting it.
A model never overwrites an intent it did not write.
_Avoid_: origin, author, source

**Ingestion**:
Bringing a newly installed wordlist into the catalog. Installing and cataloging
are separate acts.
_Avoid_: import, registration

**Export**:
Folding this machine's entries back into the shared catalog, by signature, so
that another machine inherits them. A merge and never a replacement: an entry
the catalog describes but this disk does not hold stays described, because one
machine's disk is not the census. The scan never exports on its own.
_Avoid_: sync, push, upload

### Axes

The nine dimensions along which an entry is classified. Eight are drawn from a
controlled vocabulary; **freshness** is an open axis, being a year rather than a
choice. Multi-valued except **kind**, **order**, **case** and **freshness**.
Three of the nine are established by the scan without a model.

**kind**:
What an entry physically is: `wordlist`, or one of the things installed among
the wordlists that is not one — `payload-file` delivered whole, `source-code` to
compile or run, `structured-data` to parse first, `binary`. Absence means
`wordlist`, so one grep for `kind` lists every exception. A claim that an entry
is not a wordlist must be supported by the sample the scan took, because
mis-tagging a usable list hides it from every query.

**target**:
What the wordlist enumerates: directory, file, extension, parameter, api-route,
subdomain, vhost, username, password, header, server-variable,
injection-payload, security-answer, word, ip-address, port, hash, email, domain.
`security-answer` carries the 161 entries of school, city and surname lists that
answer a knowledge-based authentication question; `word` is the lexicon aimed at
no particular slot, and is wrong wherever a more specific target fits.

**tech**:
The technology a wordlist is specific to, or `generic`.

**provenance**:
Where the words came from: curated, real-world, generated, leaked.

**shape**:
What an entry physically looks like: bare-word, relative-path, rooted-path,
name-with-extension, bare-extension, url. Decides whether a wordlist is usable
as-is, and is the leading cause of misuse. Multi-valued, because `templates/abc/`
is both a bare word and a path: only a shape of `bare-word` alone can have
extensions appended to it, which is the pairing the axis exists for.

**language**:
The natural language of the words, or `generic`.

**order**:
`alphabetical` (proven by the scan), `frequency` (asserted by a name or a
README), `suspected-frequency` (inferred by a model from head and tail),
`unknown` (default). The only axis that is part observed and part judged, so the
value states which.

**case**:
`lower` or `mixed`.

**freshness**:
The four-digit year an entry's contents belong to, stated by documentation or
inferred from the sample. Absent when nothing supports one. The open axis: a
year has no controlled vocabulary to validate against.
