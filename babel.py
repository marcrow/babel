#!/usr/bin/env python3
"""Scan wordlist sources and rebuild local.jsonl. Observes only; calls no model."""
import fnmatch, hashlib, json, random, sys
from collections import deque
from pathlib import Path

import yaml

import catalog

HEAD, TAIL, RES = 30, 10, 60


def shape_of(lines):
    def one(s):
        if "://" in s:
            return "url"
        if s.startswith("/"):
            return "rooted-path"
        if s.startswith(".") and "." not in s[1:]:
            return "bare-extension"
        return "name-with-extension" if "." in s else "bare-word"
    seen = [one(s) for s in lines if s]
    return max(set(seen), key=seen.count) if seen else "bare-word"


def scan_file(path):
    """One pass: signature, lines, sample, order, case."""
    h, n, prev, ordered, mixed = hashlib.md5(), 0, None, True, False
    head, tail, res = [], deque(maxlen=TAIL), []
    with open(path, "rb") as f:
        for raw in f:
            h.update(raw)
            line = raw.rstrip(b"\r\n")
            n += 1
            if len(head) < HEAD:
                head.append(line)
            tail.append(line)
            if len(res) < RES:
                res.append(line)
            elif (j := random.randrange(n)) < RES:
                res[j] = line
            if ordered and prev is not None and line < prev:
                ordered = False
            prev = line
            if not mixed and line.lower() != line:
                mixed = True
    d = lambda bs: [b.decode("utf-8", "replace") for b in bs]
    sample = d(head) + d(res) + d(tail)
    return {
        "sig": h.hexdigest(), "lines": n, "bytes": path.stat().st_size,
        "shape": [shape_of(sample)], "case": "mixed" if mixed else "lower",
        "order": "alphabetical" if ordered and n > 1 else "unknown",
        "sample": sample,
    }


def scan_group(d, members):
    """A directory collapsed into one entry: signature over names and sizes,
    so we never read 4,499 user-agent files to learn they are user agents."""
    h = hashlib.md5()
    total = 0
    for m in members:
        size = m.stat().st_size
        total += size
        h.update(f"{m.name}:{size}\n".encode())
    sample = []
    for m in members[:3]:
        with open(m, "rb") as f:
            sample += [l.rstrip(b"\r\n").decode("utf-8", "replace") for l in f.readlines()[:10]]
    return {
        "sig": h.hexdigest(), "files": len(members), "bytes": total,
        "shape": [shape_of(sample)], "case": "mixed", "order": "unknown",
        "sample": sample,
    }


def walk(src):
    root = Path(src["path"])
    if not root.is_dir():
        print(f"  ! source missing: {root}", file=sys.stderr)
        return
    excl, groups = src.get("exclude", []), src.get("group", [])
    done = set()
    for g in groups:
        d = root / g
        members = sorted(p for p in d.rglob("*") if p.is_file())
        if members:
            done.update(members)
            yield d.name, root.name, str(d.relative_to(root)), scan_group(d, members), [str(d)]
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p in done:
            continue
        rel = str(p.relative_to(root))
        if any(fnmatch.fnmatch(rel, e) or fnmatch.fnmatch(p.name, e) for e in excl):
            continue
        yield p.name, root.name, str(p.relative_to(root).parent), scan_file(p), [str(p)]


def main():
    cfg = yaml.safe_load(Path("config.yml").read_text())
    cat = catalog.read(catalog.CATALOG)

    found = {}
    for src in cfg["sources"]:
        for name, coll, category, facts, paths in walk(src):
            sig = facts["sig"]
            if sig in found:                      # same content, another path
                found[sig]["paths"] += paths
                continue
            q = cat.get(sig, {})
            found[sig] = {**facts, "name": name, "collection": coll, "category": category,
                          "intent": q.get("intent", "TODO"),
                          **{a: q[a] for a in ("intent_from", "target", "tech", "provenance",
                                               "language", "freshness") if a in q},
                          **{a: q[a] for a in ("shape", "order", "case") if a in q},
                          "paths": paths}

    # Samples are for qualification only. Keeping them in local.jsonl would make
    # every grep hit dump 100 lines of wordlist into the agent's context. They are
    # kept for qualified entries too, so that one entry can be requalified later.
    catalog.write(catalog.LOCAL, [catalog.local(e) for e in found.values()])
    catalog.write(catalog.SAMPLES, [{"sig": e["sig"], "sample": e["sample"]}
                                    for e in found.values()])

    gone = [e for s, e in cat.items() if s not in found]
    todo = [e for e in found.values() if e["intent"] == "TODO"]
    # same path and name, different signature: content refreshed upstream
    changed = [(e, g) for e in todo for g in gone
               if g["name"] == e["name"] and g.get("paths", [None])[0] == e["paths"][0]]

    print(f"{len(found)} entries, {len(todo)} unqualified, {len(gone)} no longer on disk")
    for e, g in changed:
        print(f"  ~ {e['name']}: content changed, intent recoverable from {g['sig'][:8]}")
    for g in gone:
        if not any(g is x[1] for x in changed):
            print(f"  - {g['name']} ({g['sig'][:8]})")


def selftest():
    import tempfile

    import qualify
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "w.txt"
        p.write_bytes(b"admin\nBackup\nzebra\n")
        f = scan_file(p)
        assert f["sig"] == hashlib.md5(p.read_bytes()).hexdigest(), "sig != md5sum"
        assert f["lines"] == 3 and f["case"] == "mixed"
        assert f["order"] == "unknown", "B < a in bytes, so this is not sorted"
        p.write_bytes(b"a\nb\nc\n")
        assert scan_file(p)["order"] == "alphabetical"
        p.write_bytes(b"/etc/passwd\n/var/log\n")
        assert scan_file(p)["shape"] == ["rooted-path"]
        p.write_bytes(b"index.php\nadmin.php\n")
        assert scan_file(p)["shape"] == ["name-with-extension"]
        p.write_bytes(b"")
        assert scan_file(p)["lines"] == 0, "empty file must not crash"
    print("selftest ok")
    qualify.selftest()


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
