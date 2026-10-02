"""Catalog load, merge and write: shared by the scan and the qualification.

Entries are keyed by signature throughout (ADR 0002). `catalogue.jsonl` is the
shared, committed catalog and carries no path; `local.jsonl` is this machine's
copy of it with bindings attached.
"""
import json
from pathlib import Path

CATALOG, LOCAL, SAMPLES = "catalogue.jsonl", "local.jsonl", "samples.jsonl"

# Properties of this machine, or bulk the agent must never grep: both are
# rebuilt by the scan and neither belongs in the shared catalog.
LOCAL_ONLY = ("paths", "sample")

# Intent provenances a model may not write over.
PROTECTED = ("harvested", "hand")

# What qualification establishes and the scan must carry forward untouched. The
# scan owns shape and case, which it measures afresh every pass, and arbitrates
# order, which is part observed and part judged. Anything here that the scan
# forgets is silently destroyed on the next walk: `kind` was, for 61 entries.
QUALIFIED = ("intent", "intent_from", "target", "tech", "provenance", "language",
             "kind", "freshness")


def read(path):
    """{signature: entry} from a JSONL file, empty if it is not there yet."""
    p = Path(path)
    if not p.exists():
        return {}
    # split("\n"), never splitlines(): samples carry bytes such as \x85 and \u2028
    # which splitlines() treats as line breaks and json.dumps leaves unescaped.
    return {e["sig"]: e for line in p.read_text().split("\n") if line.strip()
            for e in [json.loads(line)]}


def write(path, objects):
    Path(path).write_text("".join(
        json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n" for o in objects))


def shared(entry):
    """An entry as the committed catalog carries it: one line, no path, no sample."""
    return {k: v for k, v in entry.items() if k not in LOCAL_ONLY}


def local(entry):
    """An entry as this machine carries it: its bindings, but never its sample."""
    return {k: v for k, v in entry.items() if k != "sample"}


def merge(entries, deltas):
    """Fold qualification deltas into entries by signature.

    A model never overwrites an intent it did not write: that is what makes the
    hand-editable catalog of ADR 0001 real rather than nominal.
    """
    out = {sig: dict(e) for sig, e in entries.items()}
    for sig, delta in deltas.items():
        e = out.setdefault(sig, {"sig": sig})
        if delta.get("intent_from") == "model" and e.get("intent_from") in PROTECTED:
            delta = {k: v for k, v in delta.items() if k not in ("intent", "intent_from")}
        e.update(delta)
        for k in [k for k, v in e.items() if v is None]:
            del e[k]          # a delta of None clears a field, such as a settled review
    return out


def write_both(entries, deltas):
    """Write the shared catalog and this machine's copy from one merge."""
    merged = merge(entries, deltas)
    write(CATALOG, [shared(e) for e in merged.values()])
    write(LOCAL, [local(e) for e in merged.values()])
    return merged


def with_samples(entries, samples):
    """Entries carrying the sample the scan took, which is what qualification reads."""
    return [{**e, **samples[sig]} for sig, e in entries.items() if sig in samples]
