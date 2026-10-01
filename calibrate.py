#!/usr/bin/env python3
"""Throwaway: measure which model is good enough, per category, before the run.

Two lots of thirty. The documented lot is drawn from the entries whose README
text is the arbiter; that text is never shown to the model being measured. The
hard lot is drawn from the categories where failure is expected, plus the Burp
`.pay` lists as a weakly-memorised probe, and is arbitrated head to head by the
strongest model because no human text exists for it.

Each lot runs twice: with the name and directory, and blind. The gap between
the two conditions is the result — a model that only scores when it can see the
path is reciting a corpus, and will fail on the 98% of entries that are obscure.

Runs once to produce `routing.yml`, then it is dead code. No tests, by decision.
"""
import json, random, sys
from collections import defaultdict
from pathlib import Path

import yaml

import catalog
from qualify import MODEL as CHEAP
from qualify import ask_api, ask_cli, doc_for, harvest, load_taxonomy, qualify

STRONG, JUDGE = "claude-sonnet-5-5", "claude-opus-5-5"
HARD = ("Fuzzing/XSS", "Fuzzing/LFI", "Payloads", "Pattern-Matching")
LOT, SEED, ESCALATE = 30, 20261001, 6
# The subscription by default, the metered key with --api.
ASK = ask_api if "--api" in sys.argv else ask_cli

SCORE = """\
A wordlist was described by an analyst who had its documentation, and by a model
that saw only its contents. Score the model against the analyst, 0 to 2:

2 — says what the analyst says, and is specific enough to choose on
1 — broadly right but vaguer or partly wrong
0 — wrong, or so generic it would fit any wordlist

Analyst: {truth}

Model: {candidate}

Reply with one digit and nothing else.
"""

PAIR = """\
Two intents written for the same wordlist, written from its contents alone. Which
would help an agent pick the right list mid-mission? Judge specificity and
whether it says what a hit means. Reply with A, B, or = and nothing else.

A: {a}

B: {b}
"""


def draw(entries, docs):
    """Both lots, reproducibly."""
    rng = random.Random(SEED)
    documented = sorted((e for e in entries if doc_for(docs, e)), key=lambda e: e["sig"])
    burp = sorted((e for e in entries if e["name"].endswith(".pay")), key=lambda e: e["sig"])
    hard = sorted((e for e in entries if e["category"].startswith(HARD) and not doc_for(docs, e)),
                  key=lambda e: e["sig"])
    return (rng.sample(documented, min(LOT, len(documented))),
            rng.sample(hard, min(LOT - 10, len(hard))) + rng.sample(burp, min(10, len(burp))))


def run(lot, model, show_name, tax):
    """One lot, one model, one condition. No harvested text reaches the model."""
    blank = [{**e, "intent": "TODO"} for e in lot]
    deltas, report = qualify(blank, {**tax, "distinctness": 0}, ASK,
                             routing={"default": model}, show_name=show_name,
                             log=lambda m: print(f"    {m}", flush=True))
    print(f"    {len(deltas)} answered, {len(report['rejected'])} rejected")
    return deltas


def judge(prompt):
    return ASK(prompt, JUDGE).strip()[:1]


def main():
    tax, entries = load_taxonomy(), catalog.read(catalog.LOCAL)
    pool = catalog.with_samples(entries, catalog.read(catalog.SAMPLES))
    cfg = yaml.safe_load(Path("config.yml").read_text())
    docs = harvest(s["path"] for s in cfg["sources"])
    truth = {e["sig"]: doc_for(docs, e)["intent"] for e in pool if doc_for(docs, e)}
    documented, hard = draw(pool, docs)
    by_sig = {e["sig"]: e for e in documented + hard}

    # Keyed by the three things that vary, never by a string to be re-parsed.
    out, scores = {}, defaultdict(list)
    for lot_name, lot in (("documented", documented), ("hard", hard)):
        for model in (CHEAP, STRONG):
            for show in ("named", "blind"):
                print(f"  {lot_name}/{model}/{show}", flush=True)
                out[lot_name, model, show] = run(lot, model, show == "named", tax)

    # The documented lot has an arbiter: the text the model never saw.
    for (lot_name, model, show), deltas in out.items():
        if lot_name != "documented":
            continue
        for sig, d in deltas.items():
            if sig in truth:
                got = judge(SCORE.format(truth=truth[sig], candidate=d["intent"]))
                scores[model, show, by_sig[sig]["category"]].append(int(got) if got.isdigit() else 0)

    # The hard lot has none, so the strongest model arbitrates cheap against
    # strong, blind to which is which.
    wins = defaultdict(lambda: [0, 0, 0])
    for show in ("named", "blind"):
        a, b = out["hard", CHEAP, show], out["hard", STRONG, show]
        for sig in set(a) & set(b):
            flip = random.Random(sig).random() < 0.5
            x, y = (b, a) if flip else (a, b)
            v = judge(PAIR.format(a=x[sig]["intent"], b=y[sig]["intent"]))
            cat = by_sig[sig]["category"]
            if v in ("A", "B"):
                cheap_won = (v == "A") != flip
                wins[show, cat][0 if cheap_won else 1] += 1
            else:
                wins[show, cat][2] += 1

    print("\n=== documented lot, scored against the README it never saw (mean of 2)")
    for (model, show, cat), vals in sorted(scores.items()):
        print(f"  {model:30} {show:6} {cat:44} {sum(vals)/len(vals):.2f}  n={len(vals)}")
    print("\n=== hard lot, cheap vs strong, judged blind (cheap/strong/tie)")
    for (show, cat), (c, s, t) in sorted(wins.items()):
        print(f"  {show:6} {cat:44} {c}/{s}/{t}")

    # Routing: a category keeps the cheap model unless the strong one wins it.
    routing = {"default": CHEAP}
    for (show, cat), (c, s, t) in wins.items():
        if show == "blind" and s > c:
            routing[cat] = STRONG
    for (model, show, cat), vals in scores.items():
        if (model, show) == (CHEAP, "blind") and sum(vals) / len(vals) < 1.5:
            routing[cat] = STRONG

    Path("routing.yml").write_text(yaml.safe_dump({"routing": routing}, sort_keys=True))
    Path("calibration.json").write_text(json.dumps(
        {"scores": {"|".join(k): v for k, v in scores.items()},
         "wins": {"|".join(k): v for k, v in wins.items()},
         "intents": {"|".join(k): {s: d["intent"] for s, d in ds.items()}
                     for k, ds in out.items()},
         "names": {s: e["name"] for s, e in by_sig.items()}}, indent=1))
    print(f"\nwrote routing.yml: {routing}")

    # The operator arbitrates thirty entries, not thirteen hundred.
    print(f"\n=== {ESCALATE} hardest cases for you to read, strongest model included")
    lost = [c for (show, c), (ch, st, _) in wins.items() if show == "blind" and st > ch]
    worst = [e["sig"] for e in hard if e["category"] in lost] or [e["sig"] for e in hard]
    for sig in worst[:ESCALATE]:
        print(f"\n  {by_sig[sig]['name']}  [{by_sig[sig]['category']}]")
        for key, deltas in out.items():
            if key[0] == "hard" and sig in deltas:
                print(f"    {'/'.join(key[1:])}: {deltas[sig]['intent']}")
        best = qualify([{**by_sig[sig], "intent": "TODO"}], {**tax, "distinctness": 0},
                       ASK, routing={"default": JUDGE}, show_name=False)[0]
        for d in best.values():
            print(f"    {JUDGE}/blind: {d['intent']}")


if __name__ == "__main__":
    sys.exit(main())
