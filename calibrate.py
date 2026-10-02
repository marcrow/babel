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
import json, random, re, sys
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

# The judge is asked once per lot rather than once per entry: a hundred and ninety
# sequential calls to the strongest model is an afternoon, and the information is
# the same.
SCORE = """\
Each numbered case is one wordlist, described by an analyst who had its
documentation and by a model that saw only its contents. Score each model against
its own analyst, 0 to 2:

2 — says what the analyst says, and is specific enough to choose on
1 — broadly right but vaguer or partly wrong
0 — wrong, or so generic it would fit any wordlist

{cases}

Reply with one line per case, "number: digit", and nothing else.
"""

PAIR = """\
Each numbered case is one wordlist's own contents, followed by two intents
written about it. For each, say which intent would help an agent pick the right
list mid-mission.

Check every claim against the contents shown. A detail the contents do not
support is worse than no detail: an invented origin, an invented ordering or an
invented tool name should lose to a plainer sentence that is true. Length is not
specificity. Judge what a hit is said to mean, and whether it is right.

{cases}

Reply with one line per case, "number: A" or "number: B" or "number: =", and
nothing else.
"""


def draw(entries, docs):
    """Both lots, reproducibly."""
    rng = random.Random(SEED)
    documented = sorted((e for e in entries if doc_for(docs, e)), key=lambda e: e["sig"])
    burp = sorted((e for e in entries if e["name"].endswith(".pay")), key=lambda e: e["sig"])
    hard = sorted((e for e in entries if e["category"].startswith(HARD) and not doc_for(docs, e)),
                  key=lambda e: e["sig"])
    # A third of the hard lot is the weakly-memorised probe, whatever the lot size.
    probe = min(LOT // 3, len(burp))
    return (rng.sample(documented, min(LOT, len(documented))),
            rng.sample(hard, min(LOT - probe, len(hard))) + rng.sample(burp, probe))


def run(lot, model, show_name, tax):
    """One lot, one model, one condition. No harvested text reaches the model."""
    blank = [{**e, "intent": "TODO"} for e in lot]
    deltas, report = qualify(blank, {**tax, "distinctness": 0}, ASK,
                             routing={"default": model}, show_name=show_name,
                             log=lambda m: print(f"    {m}", flush=True))
    print(f"    {len(deltas)} answered, {len(report['rejected'])} rejected")
    return deltas


def judge(template, cases):
    """One call for a whole lot: {key: verdict} for the cases it answered.

    The judge does not keep to one shape between calls, and a parse that quietly
    returns nothing deletes a whole condition from the measurement, so this reads
    loosely, falls back on order, and says so when it still comes up short.
    """
    keys = list(cases)
    body = "\n\n".join(f"### {i}\n{cases[k]}" for i, k in enumerate(keys, 1))
    reply = ASK(template.format(cases=body), JUDGE)
    out = {}
    if not re.search(r"\d\s*[:.)-]\s*[0-2AB=]", reply):
        reply = ASK(template.format(cases=body), JUDGE)      # a refusal is often one-off
    for line in reply.splitlines():
        if m := re.match(r"\D*(\d+)\D+([0-2AB=])", line.strip()):
            n = int(m.group(1))
            if 1 <= n <= len(keys):
                out[keys[n - 1]] = m.group(2)
    if not out:                                  # answered in some other shape
        tokens = re.findall(r"(?<![\w])([0-2AB=])(?![\w])", reply)
        if len(tokens) == len(keys):
            out = dict(zip(keys, tokens))
    if len(out) < len(keys):
        print(f"    ! judge parsed {len(out)} of {len(keys)}: {reply[:100]!r}", flush=True)
    return out


def saved():
    """The eight conditions as the last run left them, keyed as it keyed them."""
    cal = json.load(Path("calibration.json").open())
    out = {}
    for key, intents in cal["intents"].items():
        lot_name, model, show = key.split("|")
        out[lot_name, model, show] = {sig: {"intent": i} for sig, i in intents.items()}
    return out, cal["names"]


def decide(scores, wins):
    """The routing, from evidence rather than from one judge call: four
    observations at least, and a margin rather than a single win.

    The head-to-head is aggregated at the top-level category. `Fuzzing/XSS/
    human-friendly`, `/robot-friendly` and `/Polyglots` are siblings of one
    family, and twenty entries cannot say anything about each of them alone;
    routing matches by prefix, so one line covers the family.
    """
    routing = {"default": CHEAP}
    family = defaultdict(lambda: [0, 0])
    for (show, cat), (c, s, _) in wins.items():
        if show == "blind":
            top = family[cat.split("/")[0]]
            top[0] += c
            top[1] += s
    for cat, (c, s) in family.items():
        # A proportional margin, not an absolute one: at twelve comparisons a
        # seven-to-five split is a coin toss, and routing a hundred entries to a
        # dearer model on a coin toss is how a measurement wastes money.
        if c + s >= 4 and s >= 2 * c:
            routing[cat] = STRONG
    for (model, show, cat), vals in scores.items():
        if (model, show) == (CHEAP, "blind") and len(vals) >= 4 and sum(vals) / len(vals) < 1.5:
            routing[cat] = STRONG
    return routing


def main():
    tax, entries = load_taxonomy(), catalog.read(catalog.LOCAL)
    if "--route-only" in sys.argv:
        # Re-derive the decision from the measurement already paid for.
        cal = json.load(Path("calibration.json").open())
        scores = {tuple(k.split("|")): v for k, v in cal["scores"].items()}
        wins = {(k.split("|")[0], k.split("|")[1]): v for k, v in cal["wins"].items()}
        routing = decide(scores, wins)
        Path("routing.yml").write_text(yaml.safe_dump({"routing": routing}, sort_keys=True))
        print(yaml.safe_dump({"routing": routing}, sort_keys=True))
        return
    pool = catalog.with_samples(entries, catalog.read(catalog.SAMPLES))
    cfg = yaml.safe_load(Path("config.yml").read_text())
    docs = harvest(s["path"] for s in cfg["sources"])
    truth = {e["sig"]: doc_for(docs, e)["intent"] for e in pool if doc_for(docs, e)}
    documented, hard = draw(pool, docs)
    by_sig = {e["sig"]: e for e in documented + hard}

    # Keyed by the three things that vary, never by a string to be re-parsed.
    out, scores = {}, defaultdict(list)
    if "--rejudge" in sys.argv:
        out, _ = saved()
        print(f"rejudging {sum(len(d) for d in out.values())} intents already paid for")
    else:
        for lot_name, lot in (("documented", documented), ("hard", hard)):
            for model in (CHEAP, STRONG):
                for show in ("named", "blind"):
                    print(f"  {lot_name}/{model}/{show}", flush=True)
                    out[lot_name, model, show] = run(lot, model, show == "named", tax)

    # The documented lot has an arbiter: the text the model never saw.
    for (lot_name, model, show), deltas in out.items():
        if lot_name != "documented":
            continue
        cases = {sig: f"Analyst: {truth[sig]}\n\nModel: {d['intent']}"
                 for sig, d in deltas.items() if sig in truth}
        print(f"  judging {model}/{show}: {len(cases)} cases", flush=True)
        for sig, verdict in judge(SCORE, cases).items():
            if verdict.isdigit():
                scores[model, show, by_sig[sig]["category"]].append(int(verdict))

    # The hard lot has none, so the strongest model arbitrates cheap against
    # strong, blind to which is which.
    wins = defaultdict(lambda: [0, 0, 0])
    for show in ("named", "blind"):
        a, b = out["hard", CHEAP, show], out["hard", STRONG, show]
        both = sorted(set(a) & set(b))
        flipped = {sig: random.Random(sig).random() < 0.5 for sig in both}
        cases = {}
        for sig in both:
            x, y = (b, a) if flipped[sig] else (a, b)
            # The judge sees the file, or it can only rank prose.
            lines = [l[:160] for l in (by_sig[sig].get("sample") or [])[:14]]
            cases[sig] = ("Contents:\n" + "\n".join("  " + l for l in lines)
                          + f"\n\nA: {x[sig]['intent']}\n\nB: {y[sig]['intent']}")
        print(f"  judging cheap against strong, {show}: {len(cases)} cases", flush=True)
        for sig, v in judge(PAIR, cases).items():
            cat = by_sig[sig]["category"]
            if v in ("A", "B"):
                wins[show, cat][0 if (v == "A") != flipped[sig] else 1] += 1
            else:
                wins[show, cat][2] += 1

    print("\n=== documented lot, scored against the README it never saw (mean of 2)")
    for (model, show, cat), vals in sorted(scores.items()):
        print(f"  {model:30} {show:6} {cat:44} {sum(vals)/len(vals):.2f}  n={len(vals)}")
    print("\n=== hard lot, cheap vs strong, judged blind (cheap/strong/tie)")
    for (show, cat), (c, s, t) in sorted(wins.items()):
        print(f"  {show:6} {cat:44} {c}/{s}/{t}")

    # Routing: a category keeps the cheap model unless the strong one wins it.
    routing = decide(scores, wins)

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
