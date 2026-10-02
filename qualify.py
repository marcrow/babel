#!/usr/bin/env python3
"""Qualification: write each entry's intent and axes.

One seam: `qualify(samples, taxonomy, ask) -> (deltas, report)`. The controlled
vocabulary, batch splitting, the quality gates, README precedence and intent
provenance all sit behind it. `ask` is injected by the caller, so the self-check
exercises the whole spine without a network call.
"""
import fnmatch, json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from collections import Counter
from pathlib import Path

import yaml

import catalog

BATCH, MODEL = 10, "claude-haiku-4-5-20251001"
# A sample line is clipped before it reaches a model: `pi-large.txt` is one line
# of 4.2 million digits and `uber.gif` is a picture, and neither says anything
# past its first few characters that is worth paying for.
CLIP = 200
MODEL_AXES = ("target", "tech", "provenance", "language")

PROMPT = """\
These are wordlists installed on one machine. For each entry below, say what it
is for, judging from its contents.

Write for an agent choosing between this entry and a neighbouring one. An intent
that would fit any other entry aimed at the same thing is a failed intent, so
each one must carry the fact that distinguishes this entry: the corpus, tool,
vendor or research it came from, how it was ordered, how wide it reaches, what it
deliberately leaves out. Say what a hit means, because words that look like
directories are not known directories. One or two sentences, no hedging, and
never these words: {banned}.

This is the shape of an intent, written about a wordlist that is not in this
catalog. Imitate how it works, never its words, and never write about anything
it names:

  The 400-odd Belgian town names, in Dutch and French spellings both; a hit is
  a plausible branch-office hostname, which is why the French spellings matter
  on a Walloon target and nowhere else.

Each entry stands alone: never refer to another entry in this batch, by number or
otherwise, and never number your intent.

The scan has already established the facts stated with each entry. Do not repeat
them and do not contradict them.

Axes, canonical values only; omit an axis the sample cannot support, except
tech and language, where `generic` is the answer when nothing is specific:
{vocab}
- kind: omit it when the sample is a wordlist, which is what nearly all of them
  are. Name it when the sample is plainly something else that happens to be
  installed among them: `payload-file` for something delivered or uploaded whole,
  a web shell or a crafted image; `source-code` for something compiled or run,
  an exploit or a script that generates a list; `structured-data` when the whole file is
  one document to parse, an XML tree or a JSON object — never because the lines
  of a list happen to contain HTML or XML fragments, which is still a wordlist;
  `binary` for anything compressed or not text at all. Say in the intent what it is and how it is used, and leave target
  out when nothing is being enumerated. Do not guess from an extension: a `.php`
  file holding one path per line is a wordlist, and a `.txt` file holding a shell
  script is not.
- freshness: a four-digit year the contents imply, else omit
- order: only `frequency` or `suspected-frequency`, and only from head and tail

Reply with one JSON object per entry, one per line, no prose and no code fence:
{"n":1,"intent":"...","target":["..."],"tech":["..."],"provenance":["..."],"language":["..."],"freshness":"2015"}
"""


def load_taxonomy(path="taxonomy.yml"):
    return yaml.safe_load(Path(path).read_text())


# --- controlled vocabulary ---------------------------------------------------

def canonical(tax, axis, value):
    """The canonical value, or None if it is outside the vocabulary. A model asked
    for one value often answers with a list of one, which is the same answer."""
    if isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    v = re.sub(r"\s+", "-", str(value).strip().lower())
    v = tax.get("aliases", {}).get(v, v)
    return v if v in tax["axes"][axis] else None


def validate(tax, got, entry):
    """Axes for an entry, or a reason it stays TODO."""
    axes, bad = {}, []
    for axis in MODEL_AXES:
        vals = got.get(axis) or []
        vals = [vals] if isinstance(vals, str) else vals
        for v in vals:
            c = canonical(tax, axis, v)
            if c:
                axes.setdefault(axis, []).append(c)
            else:
                bad.append(f"{axis}={v}")
    if bad:
        return None, "unknown axis value: " + ", ".join(bad)
    kind = canonical(tax, "kind", got.get("kind") or "wordlist")
    if not kind:
        return None, f"unknown axis value: kind={got.get('kind')}"
    if not axes.get("target") and kind == "wordlist":
        return None, "no target"
    if not supported(kind, entry):
        return None, f"claims {kind} but the scan's sample does not support it"
    axes = {a: sorted(set(v)) for a, v in axes.items()}
    if kind != "wordlist":
        axes["kind"] = kind        # absence means wordlist, so only oddities carry it
    if (o := got.get("order")) and entry.get("order", "unknown") == "unknown":
        c = canonical(tax, "order", o)
        if not c:
            return None, f"unknown axis value: order={o}"
        if c in ("frequency", "suspected-frequency"):
            axes["order"] = c          # `alphabetical` is the scan's to prove
    if re.fullmatch(r"(19|20)\d\d", str(got.get("freshness", "")).strip()):
        axes["freshness"] = str(got["freshness"]).strip()
    return axes, None


EXAMPLE = ("belgian town names", "branch-office hostname", "walloon target",
           "dutch and french spellings")


# A file of code or markup announces itself on its first line. A list of payloads
# does not, however much markup each of its lines contains.
CODEY = re.compile(r"""\s*(\#!|<\?|<%|<!--|<html|\#include|//|/\*|import |package |using |
                          function |class |def |\$\w+\s*=)""", re.I | re.X)
DOCUMENT = re.compile(r"\s*(<\?xml|<!DOCTYPE|<html|[{\[])", re.I)


def supported(kind, entry):
    """Whether the scan's own sample backs a claim that an entry is not a wordlist.
    Mis-tagging a usable list hides it from every query, which is worse than
    leaving it TODO, so a claim the sample cannot support is refused."""
    head = (entry.get("sample") or [""])[0]
    if kind == "structured-data":
        return bool(DOCUMENT.match(head))
    if kind in ("payload-file", "source-code"):
        return bool(CODEY.match(head)) or (entry.get("lines") or 0) <= 3
    if kind == "binary":
        return any("\ufffd" in line for line in entry.get("sample") or [])
    return True


def bad_intent(tax, intent):
    """Why an intent is not worth having, if it is not. Applied to every intent
    that reaches the catalog, whoever wrote it."""
    if len(intent) < tax.get("min_intent", 30):
        return "intent too short to be worth having"
    flat = " ".join(intent.lower().split())
    if any(bit in flat for bit in EXAMPLE):
        return "copied the prompt's example instead of reading the sample"
    if re.search(r"(?i)\bentry (number )?\d|\bthe (first|second|third) entry\b", intent):
        return "refers to another entry in its batch"
    for w in tax.get("banned", []):
        if re.search(r"\b" + re.escape(w) + r"\b", intent, re.I):
            return f"filler vocabulary: {w!r}"


# --- harvesting what a human already wrote -----------------------------------

SECTION = re.compile(r"^##+\s+(\S+)[^\n]*$", re.M)
STALE = re.compile(r"(?i)no updates|years old|outdated|no longer maintained|deprecated")


def _clean(body):
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)          # markdown links
    body = re.sub(r"\[!\w+\]", "", body)                           # > [!WARNING]
    return body.replace("**", "").replace("`", "")


def read_intent(body):
    """One intent out of a README section: 'Use for:' first, prose otherwise,
    plus any staleness warning. One parser for every format in the wild."""
    lines = [l.strip().lstrip("> ").strip() for l in _clean(body).splitlines()]
    keep = [l for l in lines if l and not l.startswith(("#", "-", "*", "|", "```", "!["))]
    use = [l[len("use for:"):].strip() for l in keep if l.lower().startswith("use for:")]
    prose = [l for l in keep if not re.match(r"(?i)(use for|source|creation date|author)\s*:", l)
             and not l.endswith(":")                # a line introducing a list
             and not re.match(r"(?i)^\S*\s*:?\s*https?://", l)]
    warn = [l for l in prose if STALE.search(l)]
    parts = use + [l for l in prose if l not in warn][:1] + warn[:1]
    intent = " ".join(p.rstrip(".") + "." for p in dict.fromkeys(parts) if p)
    year = re.search(r"\b(19[89]\d|20[0-3]\d)\b", " ".join(keep))
    return (intent[:600] if len(intent) > 25 else None), (year.group(1) if year else None)


def harvest(sources):
    """The intents a human already wrote, shipped with the collections, as
    patterns to match entry names against."""
    docs = []
    for root in sources:
        root = Path(root)
        if not root.is_dir():
            continue
        for rm in sorted(root.rglob("*")):
            if not rm.is_file() or not rm.name.lower().startswith("readme"):
                continue
            text = rm.read_text(errors="replace")
            parts = SECTION.split(text)
            for head, body in zip(parts[1::2], parts[2::2]):
                pat = head.strip("`").strip("_:, ")
                if "." not in pat and "*" not in pat:
                    continue                      # a prose heading, not a name
                intent, year = read_intent(body)
                if intent:
                    docs.append({"collection": root.name, "pattern": pat, "intent": intent,
                                 "category": str(rm.parent.relative_to(root)), "freshness": year})
    return docs


def doc_for(docs, e):
    """The most specific documented intent matching an entry, if one exists."""
    best = None
    for d in docs:
        cat = e.get("category", ".")
        if d["collection"] != e.get("collection"):
            continue
        if d["category"] != "." and not (cat == d["category"] or cat.startswith(d["category"] + "/")):
            continue
        if not fnmatch.fnmatch(e["name"].lower(), d["pattern"].lower()):   # READMEs misspell case
            continue
        key = (len(d["category"]), "*" not in d["pattern"], len(d["pattern"]))
        if best is None or key > best[0]:
            best = (key, d)
    return best[1] if best else None


# --- the prompt --------------------------------------------------------------

def prompt_for(tax, batch, show_name=True):
    vocab = "\n".join(f"- {a}: {', '.join(tax['axes'][a])}" for a in MODEL_AXES)
    out = [PROMPT.replace("{vocab}", vocab).replace("{banned}", ", ".join(tax["banned"]))]
    for n, e in enumerate(batch, 1):
        head = [f"### {n}"]
        if show_name:
            head.append(f"name: {e['name']}")
            if e.get("category", ".") != ".":
                head.append(f"category: {e['category']}")
        size = f"lines: {e['lines']}" if "lines" in e else f"files: {e.get('files', '?')}"
        facts = f"{size}  shape: {'/'.join(e.get('shape') or ['unknown'])}  " \
                f"case: {e.get('case', 'unknown')}  order: {e.get('order', 'unknown')}"
        lines = [l[:CLIP] + " …clipped" if len(l) > CLIP else l for l in e.get("sample", [])]
        out.append("\n".join(head + [facts, "sample:"] + ["  " + l for l in lines]))
    return "\n\n".join(out)


def parse(reply):
    """One JSON object per line, or a JSON array: models do both."""
    text = re.sub(r"^```\w*$", "", reply.strip(), flags=re.M).strip()
    if text.startswith("["):
        try:
            return json.loads(text)
        except ValueError:
            pass
    out = []
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def model_for(routing, category):
    """Longest matching category prefix wins; one model for everything by default."""
    keys = [k for k in routing if k != "default" and (category == k or category.startswith(k + "/"))]
    return routing[max(keys, key=len)] if keys else routing.get("default", MODEL)


# --- the seam ----------------------------------------------------------------

def qualify(samples, taxonomy, ask, docs=(), routing=None, batch=BATCH,
            show_name=True, confirm=None, log=lambda m: None):
    """Qualify the entries that are still TODO, and give an entry whose intent a
    model may not write the axes it is missing. Returns deltas keyed by signature
    plus a report, and returns no deltas at all if the distinctness gate fails.

    Every intent that reaches the catalog passes the same two gates, whoever
    wrote it: the `ronin-wordlists` failure does not become acceptable because a
    human was the one who repeated himself.
    """
    tax, routing = taxonomy, routing or {}
    deltas, rejected, todo, skipped = {}, [], [], 0

    # Pass two: the intents a human already wrote. A sentence two entries share
    # is not an intent for either of them, so both fall through to the model.
    claimed = {}
    for e in samples:
        if e.get("intent", "TODO") == "TODO" and (d := doc_for(docs, e)):
            claimed.setdefault(d["intent"], []).append((e, d))
    for text, claims in claimed.items():
        why = (f"documentation covers {len(claims)} entries with one sentence"
               if len(claims) > 1 else bad_intent(tax, text))
        for e, d in claims:
            # A year stated by documentation is a fact about the entry even when
            # the sentence around it is no intent for it, so it is kept either way.
            delta = {"freshness": d["freshness"]} if d["freshness"] else {}
            if why:
                rejected.append((e["name"], f"harvested: {why}"))
            else:
                delta |= {"intent": text, "intent_from": "harvested"}
            if delta:
                deltas[e["sig"]] = delta
    harvested = sum("intent" in d for d in deltas.values())

    # Pass three: what documentation did not cover, plus any entry still missing
    # the axis an agent queries first.
    for e in samples:
        current = {**e, **deltas.get(e["sig"], {})}
        if current.get("intent", "TODO") != "TODO" and current.get("target"):
            skipped += 1
        else:
            todo.append(current)

    batches = []
    for model in sorted({model_for(routing, e.get("category", ".")) for e in todo}):
        group = [e for e in todo if model_for(routing, e.get("category", ".")) == model]
        batches += [(model, c, prompt_for(tax, c, show_name))
                    for c in (group[i:i + batch] for i in range(0, len(group), batch))]
    est = sum(len(p) for _, _, p in batches) // 4
    report = {"seen": len(samples), "skipped": skipped, "harvested": harvested,
              "from_model": 0, "rejected": rejected, "est_tokens": est,
              "distinctness": 1.0, "interrupted": False, "declined": False, "ok": True}

    if ask is None or not batches:
        return gate(tax, samples, deltas, report)
    if confirm and not confirm(est, len(batches), len(todo)):
        report["declined"] = True
        return {}, report

    for n, (model, chunk, prompt) in enumerate(batches, 1):
        log(f"[{n}/{len(batches)}] {len(chunk)} entries -> {model}")
        try:
            got = {int(g["n"]): g for g in parse(ask(prompt, model))
                   if str(g.get("n", "")).strip().isdigit()}
        except KeyboardInterrupt:
            report["interrupted"] = True      # keep the batches already answered
            break
        except Exception as exc:
            rejected += [(e["name"], f"model call failed: {exc}") for e in chunk]
            continue
        for i, e in enumerate(chunk, 1):
            if not (g := got.get(i)):
                rejected.append((e["name"], "no answer from the model"))
                continue
            # An intent the model did not write is not the model's to replace.
            writing = (e.get("intent", "TODO") == "TODO"
                       or e.get("intent_from") not in catalog.PROTECTED)
            intent = str(g.get("intent", "")).strip()
            if writing and (why := bad_intent(tax, intent)):
                rejected.append((e["name"], why))
                continue
            axes, why = validate(tax, g, e)
            if why:
                rejected.append((e["name"], why))
                continue
            delta = {**axes, **({"intent": intent, "intent_from": "model"} if writing else {})}
            # What documentation stated outranks what the model inferred.
            deltas[e["sig"]] = {**delta, **deltas.get(e["sig"], {})}

    return gate(tax, samples, deltas, report)


def gate(tax, samples, deltas, report):
    """The distinctness gate, measured over every intent the catalog would then
    carry rather than over this run alone: resumability turns one pass into many
    small runs, and repetition across them has to be caught just the same."""
    intents = [i for e in samples
               for i in [{**e, **deltas.get(e["sig"], {})}.get("intent", "TODO")] if i != "TODO"]
    report["from_model"] = sum(d.get("intent_from") == "model" for d in deltas.values())
    if intents:
        report["distinctness"] = round(len(set(intents)) / len(intents), 3)
        if report["distinctness"] < tax.get("distinctness", 0.95):
            report["ok"] = False
            return {}, report          # a bad run cannot become the catalog
    return deltas, report


# --- the census --------------------------------------------------------------

def census(entries, tax):
    """What each axis is actually carrying, so a vocabulary nothing uses, or a
    value that is a synonym of another, becomes visible."""
    out = []
    axes = {**tax["axes"], **{a: [] for a in tax.get("open_axes", [])}}
    for axis, values in axes.items():
        counts, missing = Counter(), 0
        for e in entries:
            v = e.get(axis)
            v = [v] if isinstance(v, str) else (v or [])
            counts.update(v)
            missing += not v
        out.append({"axis": axis, "counts": counts, "missing": missing,
                     # an open axis has no vocabulary, so nothing can fall outside it
                     "unused": [v for v in values if not counts.get(v)],
                     "outside": sorted(set(counts) - set(values)) if values else []})
    return out


# --- the real model call -----------------------------------------------------

SYSTEM = "You catalogue wordlists. Answer exactly as asked, with no preamble."


class Exhausted(KeyboardInterrupt):
    """The subscription's limit, reached mid-run. Inherits from KeyboardInterrupt
    so the run keeps the batches it has already paid for and stops there."""


def ask_cli(prompt, model, thinking="1024"):
    """The subscription path: Claude Code headless. No tools and no system prompt
    of its own, so the model is shown the qualification prompt and nothing else,
    and runs outside this repo so no AGENTS.md or plugin of ours colours an intent.

    Thinking is what buys a specific intent over an interchangeable one, and a
    budget is what keeps a batch at twenty seconds rather than ninety.
    """
    cmd = ["claude", "-p", "--model", model, "--restricted", "--tools", "",
           "--strict-mcp-config", "--no-session-persistence",
           "--output-format", "json", "--system-prompt", SYSTEM]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       cwd=tempfile.gettempdir(),
                       env={**os.environ, "MAX_THINKING_TOKENS": str(thinking)})
    if r.returncode or not r.stdout.strip():
        why = (r.stderr or r.stdout)[-400:]
        raise (Exhausted(why) if re.search(r"(?i)limit|quota|rate", why) else RuntimeError(why))
    out = json.loads(r.stdout)
    if out.get("is_error"):
        raise RuntimeError(str(out.get("result"))[:400])
    return out["result"]


def ask_api(prompt, model, tries=3):
    """The metered path: Messages API over the standard library, no SDK."""
    body = json.dumps({"model": model, "max_tokens": 8192,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", body,
        {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
         "content-type": "application/json"})
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return "".join(c.get("text", "") for c in json.load(r)["content"])
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 529) or attempt == tries:
                raise
            time.sleep(5 * attempt)
    raise RuntimeError("unreachable")


# --- the caller --------------------------------------------------------------

def main(argv):
    cfg = yaml.safe_load(Path("config.yml").read_text())
    tax = load_taxonomy()
    entries, samples = catalog.read(catalog.LOCAL), catalog.read(catalog.SAMPLES)
    if not entries:
        sys.exit("no local.jsonl: run babel.py first")
    pool = catalog.with_samples(entries, samples)
    q = cfg.get("qualify") or {}
    # What the calibration decided, if it has run.
    if Path("routing.yml").exists():
        q = {**q, **yaml.safe_load(Path("routing.yml").read_text())}

    if "--census" in argv:
        for axis in census(list(entries.values()), tax):
            print(f"\n{axis['axis']}  ({axis['missing']} entries carry no value)")
            for v, n in axis["counts"].most_common():
                print(f"  {n:6}  {v}")
            for label in ("unused", "outside"):
                if axis[label]:
                    print(f"  {label}: {', '.join(axis[label])}")
        return

    docs = harvest(s["path"] for s in cfg["sources"])
    if (i := next((n for n, a in enumerate(argv) if a == "--only"), None)) is not None:
        want = argv[i + 1]
        pool = [e for e in pool if e["name"] == want or e["sig"].startswith(want)]
        if not pool:
            sys.exit(f"no entry named {want} (its sample must be in samples.jsonl)")
        docs = ()          # requalifying is asking the model; the harvest had its turn
        for e in pool:
            if e.get("intent_from") == "hand" and "--force" not in argv:
                sys.exit(f"{e['name']} was corrected by hand; --force to overwrite it")
            e["intent"] = "TODO"
            # --force is the entry surrendering its protection, so the merge lets
            # the model's intent through.
            entries[e["sig"]].pop("intent_from", None)

    metered = "--api" in argv
    thinking = q.get("thinking", 1024)
    ask = ask_api if metered else lambda p, m: ask_cli(p, m, thinking)

    def confirm(est, batches, n):
        print(f"{n} entries, {batches} batches, ~{est:,} input tokens, "
              + ("billed to ANTHROPIC_API_KEY" if metered else "on this machine's subscription"))
        return "--yes" in argv or input("proceed? [y/N] ").strip().lower() == "y"

    deltas, report = qualify(
        pool, tax, None if "--harvest-only" in argv else ask, docs=docs,
        routing=q.get("routing") or {"default": MODEL}, batch=q.get("batch", BATCH),
        confirm=confirm, log=lambda m: print(m, flush=True))

    print(f"\n{report['harvested']} harvested, {report['from_model']} from a model, "
          f"{report['skipped']} already qualified, {len(report['rejected'])} rejected")
    print(f"distinctness {report['distinctness']} (threshold {tax['distinctness']})")
    for name, why in report["rejected"]:
        print(f"  ! {name}: {why}")
    if report["declined"]:
        sys.exit("declined, nothing written")
    if not report["ok"]:
        sys.exit("intents too repetitive to be useful: nothing written")
    catalog.write_both(entries, deltas)
    print(f"wrote {len(deltas)} entries to {catalog.CATALOG} and {catalog.LOCAL}"
          + (" (interrupted: rerun to finish)" if report["interrupted"] else ""))


# --- the self-check ----------------------------------------------------------

def selftest():
    """Asserts on what the seam returns, never on how it got there. The model is
    faked, so this makes no network call."""
    import tempfile
    tax, seen = load_taxonomy(), []

    def ask_with(*answers):
        def ask(prompt, model):
            seen.append(prompt)
            return "\n".join(json.dumps({"n": i + 1, **a}) for i, a in enumerate(answers))
        return ask

    def entry(sig, name, **kw):
        return {"sig": sig, "name": name, "collection": "seclists", "lines": 100,
                "category": "Discovery/DNS", "shape": ["bare-word"], "case": "lower",
                "order": "unknown", "intent": "TODO", "sample": ["admin", "mail"], **kw}

    GOOD = {"intent": "Subdomain labels zone-transferred from Alexa in 2015; a hit names a host "
                      "that answered DNS then, not one that answers now.",
            "target": ["subdomains"], "tech": ["PHP", "php7"], "provenance": ["real-world"],
            "language": ["en"], "freshness": "2015"}

    # an alias resolves to its canonical value, and the intent lands on the entry
    d, r = qualify([entry("s1", "a.txt")], tax, ask_with(GOOD))
    assert d["s1"]["target"] == ["subdomain"], d["s1"]
    assert d["s1"]["tech"] == ["php"], "PHP and php7 must collapse onto php"
    assert d["s1"]["intent_from"] == "model" and d["s1"]["freshness"] == "2015"
    assert r["ok"] and r["from_model"] == 1 and not r["rejected"]

    # an unknown axis value is rejected: the entry stays TODO and is named
    d, r = qualify([entry("s2", "b.txt")], tax, ask_with({**GOOD, "tech": ["cobol"]}))
    assert d == {} and r["rejected"][0][0] == "b.txt" and "cobol" in r["rejected"][0][1], r

    # banned filler vocabulary is rejected
    d, r = qualify([entry("s3", "c.txt")], tax, ask_with(
        {**GOOD, "intent": "A wordlist of common terms, used for fuzzing any web application."}))
    assert d == {} and "filler" in r["rejected"][0][1], r

    # the same sentence every time fails the run and writes nothing at all
    d, r = qualify([entry(f"q{i}", f"{i}.txt") for i in range(4)], tax,
                   ask_with(*[dict(GOOD)] * 4))
    assert d == {} and not r["ok"] and r["distinctness"] == 0.25, r

    # a harvested intent is kept, and a model is not allowed to replace it
    docs = [{"collection": "seclists", "category": "Discovery/DNS", "pattern": "sub*",
             "intent": "Subdomains zone-transferred from Alexa in 2015, several years old.",
             "freshness": "2015"}]
    seen.clear()
    d, r = qualify([entry("h1", "subdomains-top1million-5000.txt")], tax, ask_with(GOOD), docs=docs)
    assert d["h1"]["intent"].startswith("Subdomains") and d["h1"]["intent_from"] == "harvested"
    assert d["h1"]["freshness"] == "2015" and r["harvested"] == 1 and r["from_model"] == 0
    assert d["h1"]["target"] == ["subdomain"], "the axes it lacks still come from the model"
    assert "Subdomains zone-transferred" not in seen[0], "its intent is not shown to the model"

    # one sentence covering a family of entries is not an intent for any of them
    family = [{"collection": "seclists", "category": "Discovery/DNS", "pattern": "raft-*",
               "intent": "Directory and file brute-forcing leading to identification of "
                         "vulnerabilities in web applications.", "freshness": "2011"}]
    pins = {**GOOD, "target": ["password"], "intent":
            "Four-digit PINs ordered by how often they appear in breach corpora; a hit is a PIN "
            "someone actually chose."}
    d, r = qualify([entry("f1", "raft-small.txt"), entry("f2", "raft-large.txt")],
                   tax, ask_with(GOOD, pins), docs=family)
    assert r["harvested"] == 0 and r["from_model"] == 2
    assert all(x["intent_from"] == "model" for x in d.values())
    assert any("one sentence" in why for _, why in r["rejected"]), r["rejected"]
    assert d["f1"]["freshness"] == "2011", "the year it states is still a fact about each member"

    # documentation that is itself filler is rejected like anything else
    weak = [{"collection": "seclists", "category": "Discovery/DNS", "pattern": "w*",
             "intent": "A wordlist of common terms, various.", "freshness": None}]
    d, r = qualify([entry("w1", "w.txt")], tax, ask_with(GOOD), docs=weak)
    assert d["w1"]["intent_from"] == "model" and "filler" in r["rejected"][0][1], r

    # an intent corrected by hand keeps its text while the axes are filled in
    d, r = qualify([entry("k1", "d.txt", intent="Mine, written by hand and worth keeping.",
                          intent_from="hand")], tax, ask_with(GOOD))
    assert "intent" not in d["k1"] and "intent_from" not in d["k1"], d["k1"]
    assert d["k1"]["target"] == ["subdomain"], "axes are still worth asking for"

    # an entry already carrying both an intent and its axes is not sent again
    seen.clear()
    d, r = qualify([entry("k2", "e.txt", intent="Earlier, by a model.", intent_from="model",
                          target=["file"])], tax, ask_with(GOOD))
    assert d == {} and seen == [] and r["skipped"] == 1, r

    # the gate measures the catalog, not the run: a model repeating an intent the
    # catalog already carries fails just as surely
    d, r = qualify([entry("c1", "f.txt", intent=GOOD["intent"], intent_from="hand",
                          target=["file"]), entry("c2", "g.txt")], tax, ask_with(GOOD))
    assert d == {} and not r["ok"] and r["distinctness"] == 0.5, r

    # merging is keyed by signature, not by name or path
    d, _ = qualify([entry("m1", "common.txt"), entry("m2", "common.txt", sample=["1234"])],
                   tax, ask_with(GOOD, pins))
    assert set(d) == {"m1", "m2"} and d["m1"]["intent"] != d["m2"]["intent"]
    kept = catalog.merge({"m1": {"sig": "m1", "intent": "Mine.", "intent_from": "hand"}}, d)
    assert kept["m1"]["intent"] == "Mine.", "a model must not overwrite a hand correction"
    assert kept["m1"]["target"] == ["subdomain"] and kept["m2"]["intent"] == pins["intent"]

    # a grouped entry is qualified from a sample of its members
    seen.clear()
    agents = {**GOOD, "target": ["header"], "intent":
              "User-Agent strings collected per browser family across 4,499 files; a hit is a "
              "header value to send, never a path to request."}
    d, _ = qualify([{"sig": "g1", "name": "User-Agents", "collection": "seclists",
                     "category": "Fuzzing/User-Agents", "files": 4499, "intent": "TODO",
                     "shape": ["name-with-extension"], "case": "mixed", "order": "unknown",
                     "sample": ["Mozilla/5.0 (Windows NT 6.1; WOW64) like Gecko"]}],
                   tax, ask_with(agents))
    assert "Mozilla/5.0" in seen[0] and "files: 4499" in seen[0], seen[0]
    assert d["g1"]["target"] == ["header"]

    # a line too long to be worth paying for is clipped before it is sent
    seen.clear()
    qualify([entry("p1", "pi-large.txt", sample=["3." + "1415926535" * 500])], tax,
            ask_with(GOOD))
    header = len(prompt_for(tax, [], True))      # measure the entry, not the instructions
    assert "…clipped" in seen[0] and len(seen[0]) - header < 1000, len(seen[0]) - header

    # the blind condition shows the model nothing but the sample and the facts
    seen.clear()
    qualify([entry("b1", "secret-name.txt")], tax, ask_with(GOOD), show_name=False)
    assert "secret-name.txt" not in seen[0] and "Discovery/DNS" not in seen[0]

    # one grep hit costs the agent one entry, and no machine of ours
    line = json.dumps(catalog.shared(
        {"sig": "a", "intent": "One.", "paths": ["/usr/share/seclists/x"], "sample": ["y"]}))
    assert "\n" not in line and "/usr/share" not in line and "sample" not in line, line

    # the formats in the wild, through one parser
    with tempfile.TemporaryDirectory() as t:
        root = Path(t) / "seclists"
        (root / "Discovery").mkdir(parents=True)
        (root / "Discovery" / "README.md").write_text(
            "# Web discovery\n\n"
            "## AdobeXML.fuzz.txt\nUse for: Discovering sensitive filepaths of "
            "**Adobe ColdFusion**\n\nCreation date: Aug 27, 2012\n\n"
            "No updates have been made to this list since its creation.\n\n"
            "## `subdomains-top1million-*`\n\n> [!WARNING]\n> These are several years old, "
            "they were made in 2015.\n\nZone-transfered from Amazon's Alexa.com in 2015.\n\n"
            "### Not a filename\nIgnore me.\n")
        docs = harvest([root])
    by = {d["pattern"]: d for d in docs}
    assert set(by) == {"AdobeXML.fuzz.txt", "subdomains-top1million-*"}, list(by)
    assert "ColdFusion" in by["AdobeXML.fuzz.txt"]["intent"]
    assert by["AdobeXML.fuzz.txt"]["freshness"] == "2012"
    assert "several years old" in by["subdomains-top1million-*"]["intent"], "staleness must survive"
    assert by["subdomains-top1million-*"]["freshness"] == "2015"
    e = entry("x", "subdomains-top1million-5000.txt", category="Discovery")
    assert doc_for(docs, e)["pattern"] == "subdomains-top1million-*"
    assert doc_for(docs, entry("y", "nothing-like-it.txt", category="Discovery")) is None

    # routing is data: a category sends its entries elsewhere, by longest prefix
    routing = {"default": "cheap", "Payloads": "strong"}
    assert model_for(routing, "Payloads/File-Names") == "strong"
    assert model_for(routing, "Discovery/DNS") == "cheap"

    # a sample carrying the separators that are not line breaks survives a round trip
    with tempfile.TemporaryDirectory() as t:
        f = Path(t) / "s.jsonl"
        catalog.write(f, [{"sig": "u1", "sample": ["a\u2028b", "c\x85d"]},
                          {"sig": "u2", "sample": ["ok"]}])
        back = catalog.read(f)
    assert set(back) == {"u1", "u2"} and back["u1"]["sample"] == ["a\u2028b", "c\x85d"]

    # a list of payloads is a wordlist, whatever its lines look like
    d, r = qualify([entry("x6", "XSS-Jhaddix.txt", lines=110,
                          sample=["'\"--></style></script><script>alert(1)</script>"])],
                   tax, ask_with({**GOOD, "target": ["injection-payload"], "kind": "payload-file"}))
    assert d == {} and "payload-file" in r["rejected"][0][1], r

    # an entry that is not a wordlist at all is kept, marked, and needs no target
    shell = {"n": 1, "kind": "WebShell", "tech": ["php"],
             "intent": "A single-file PHP backdoor that shells out through $_GET; it is uploaded "
                       "to a target, never fuzzed with."}
    d, r = qualify([entry("x1", "cmd.php", sample=["<?php system($_GET['cmd']); ?>"])],
                   tax, ask_with(shell))
    assert d["x1"]["kind"] == "payload-file" and "target" not in d["x1"], d["x1"]
    assert not r["rejected"], r["rejected"]

    # one value answered as a list of one is the same value
    d, _ = qualify([entry("o1", "top-1000.txt")], tax,
                   ask_with({**GOOD, "order": ["frequency"], "kind": ["wordlist"]}))
    assert d["o1"]["order"] == "frequency" and "kind" not in d["o1"], d["o1"]

    # a claim of structured-data has to be supported by the sample the scan took
    d, r = qualify([entry("x4", "payloads.txt", sample=["<img src=x onerror=alert(1)>"])],
                   tax, ask_with({**GOOD, "kind": "structured-data"}))
    assert d == {} and "does not support it" in r["rejected"][0][1], r
    d, r = qualify([entry("x5", "vectors.xml", sample=['<?xml version="1.0"?>', "<xss/>"])],
                   tax, ask_with({**GOOD, "kind": "structured-data"}))
    assert d["x5"]["kind"] == "structured-data", d

    # a wordlist still owes a target, and an unknown kind is rejected like any value
    d, r = qualify([entry("x2", "y.txt")], tax, ask_with({**GOOD, "target": []}))
    assert d == {} and r["rejected"][0][1] == "no target", r
    d, r = qualify([entry("x3", "z.txt")], tax, ask_with({**GOOD, "kind": "spreadsheet"}))
    assert d == {} and "kind=spreadsheet" in r["rejected"][0][1], r

    # the census counts what the vocabulary is actually carrying
    axes = {a["axis"]: a for a in census(
        [{"target": ["file"]}, {"target": ["file", "directory"]}, {}], tax)}
    assert axes["target"]["counts"]["file"] == 2 and axes["target"]["missing"] == 1
    assert "vhost" in axes["target"]["unused"] and not axes["target"]["outside"]
    assert axes["freshness"]["unused"] == [] and axes["freshness"]["outside"] == []

    print("qualify selftest ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main(sys.argv[1:])
