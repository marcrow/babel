# Babel

A catalog describing every wordlist installed on this machine, so that an agent on
a mission can tell what each one is for and choose between them.

It currently describes **1,373 entries, each with its own intent** — no two share a
sentence. The public project with the closest schema, `ronin-wordlists`, carries 43
distinct summaries across 2,285 entries; writing sentences that are merely accurate
is the failure this one is built to avoid.

```
$ rg '"tech":\[[^]]*"magento"' local.jsonl | jq -r '[.lines,.name,.intent]|@tsv'
16544  sitemap-magento.txt  The complete file tree of a Magento 1.x storefront
                            extracted from its sitemap, reaching into skin, media,
                            lib, and app directories; a hit identifies the shop
                            software and major subdirectories.
40618  magento.txt          Magento installation files, modules, and configuration
                            at stable depths only […]; culled to exclude test
                            artefacts and duplicate fragments.
```

Two lists for one technology, and the sentences say which is which and what a hit
would mean. Choosing between them without opening either is the whole deliverable.

It is a file, queried with `rg` and `jq`. There is no server, no daemon and no MCP,
and that is a decision rather than an omission: see
[ADR 0001](docs/adr/0001-frozen-catalog-queried-with-grep.md).

## What is where

| | |
|---|---|
| `catalogue.jsonl` | **the catalog**, committed and shareable. No absolute path, so it publishes as is |
| `local.jsonl` | this machine's copy, with the paths attached. Local, rebuilt by the scan |
| `samples.jsonl` | 100 lines sampled from each wordlist, for qualification only. Local, large |
| `taxonomy.yml` | the controlled vocabulary, the banned filler, the thresholds. All data |
| `routing.yml` | which model qualifies which category, written by the calibration |
| `config.yml` | your sources and their exclusions. Local; copy `config.example.yml` |

Only `catalogue.jsonl` is the catalog. The other two JSONL files are derived and
gitignored.

## On a new machine

```sh
cp config.example.yml config.yml     # then point `sources` at your wordlists
python3 babel.py                     # ~60s over 2.2 GB: hashes, samples, measures
```

The scan rebuilds `local.jsonl` from the committed catalog **by content signature**,
so a new machine inherits every intent for nothing, even where the paths differ.
That is the whole point of [ADR 0002](docs/adr/0002-content-signature-identity.md).
Nothing calls a model yet at this stage.

## Qualifying what is not yet described

```sh
python3 qualify.py                   # everything still TODO
python3 qualify.py --only Payloads   # one family, or one entry by name
python3 qualify.py --sample 40 --seed 1   # a rehearsal: writes nothing, prints everything
python3 qualify.py --read 25         # read a random sample of what is written
python3 qualify.py --census          # what each axis actually carries
```

Runs on this machine's Claude Code subscription by default, `--api` for a metered
key. The estimated token cost is printed before the first call and the run can be
declined there. Progress is reported per batch; an interrupted run keeps the
batches it has paid for; rerunning sends only what is still `TODO`. One pass at a
time — a second refuses to start, because both would write the catalog whole.

Two gates stand between a model and the catalog: an intent repeated by a second
entry is refused and retried, and a run that repeats itself wholesale is refused
entirely, writing nothing but keeping its work in `refused-run.jsonl`. Filler
vocabulary is rejected, and a value outside `taxonomy.yml` is never recorded —
though it no longer costs the sentence, only itself, and is reported as one line to
add.

## Correcting an intent

Edit the line in `catalogue.jsonl`, set `"intent_from":"hand"`, and run
`python3 babel.py`. No model will ever overwrite it. Corrections are the point, not
an exception: 11 of the current intents are hand-written, because the model declines
to describe live web-shell code.

## Choosing which model to trust

```sh
python3 calibrate.py                 # measures, then writes routing.yml
python3 calibrate.py --route-only    # re-derive the decision without paying again
```

Two lots of thirty, each run with the filename shown and hidden, scored against
README text the model never sees. The gap between those two conditions is the
result: a model that only scores with the path in view is reciting a corpus and
will fail on the 98% of entries that are obscure. It measured no such gap, and
routes only `Payloads` to the dearer model.

## Checks

```sh
python3 babel.py --selftest          # both self-checks, 0.12s, no network call
```

Plain `assert`, no framework, a faked model. The qualification seam is the only
thing tested, and no test calls a model.

## Reading further

- **[`skills/wordlists/SKILL.md`](skills/wordlists/SKILL.md)** — how an agent picks a
  wordlist from the catalog. The audience this project exists for.
- **[`CONTEXT.md`](CONTEXT.md)** — the project's language. Nine axes, and the terms
  this codebase refuses.
- **[`docs/adr/`](docs/adr/)** — the two decisions that shape everything else.
- **[`.scratch/qualification/`](.scratch/qualification/)** — the spec, and the nine
  tickets. Seven are done; `08` and `09` are open, both found by an agent using the
  catalog in earnest.
