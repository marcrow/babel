#!/usr/bin/env python3
"""Prove a shared catalogue.jsonl projects onto wordlists at paths we never saw.

The catalog is keyed by content signature and carries no path (ADR 0002), so it
has to survive meeting a new environment: another machine, or this one after a
source moves. These checks run the scan the way a stranger would -- their
config, their disk, our catalogue.jsonl -- and assert the qualification work
lands on the bindings they actually have.
"""
import hashlib, subprocess, sys, tempfile
from pathlib import Path

import yaml

import catalog

BABEL = Path(__file__).parent / "babel.py"


def run(cwd, *args):
    return subprocess.run([sys.executable, str(BABEL), *args], cwd=cwd, text=True,
                          capture_output=True, check=True).stdout


def scan(cwd, *paths):
    """Run the scan as a stranger does: their config, their cwd, our catalog."""
    (cwd / "config.yml").write_text(yaml.safe_dump(
        {"sources": [{"path": str(p), "exclude": ["*.md"]} for p in paths],
         "qualify": {"batch": 10, "thinking": 0}}))
    return run(cwd), catalog.read(cwd / catalog.LOCAL)


def seed(t, root, body=b"admin\nbackup\n"):
    """A one-wordlist source under `root`, and a catalog that already qualified it."""
    d = t / root / "Discovery"
    d.mkdir(parents=True)
    (d / "common.txt").write_bytes(body)
    sig = hashlib.md5(body).hexdigest()
    catalog.write(t / catalog.CATALOG, [{
        "sig": sig, "name": "common.txt", "collection": Path(root).name,
        "category": "Discovery", "intent": "Short directory names seen on most hosts.",
        "intent_from": "hand", "target": ["directory"], "tech": ["generic"]}])
    return sig, d / "common.txt"


def moved():
    """A source that moves keeps its signature and its intent, and rebinds."""
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        sig, before = seed(t, "a/seclists")
        _, local = scan(t, before.parent.parent)
        assert sig in local, "a qualified entry must be found on first scan"
        assert local[sig]["paths"] == [str(before)]
        assert local[sig]["intent_from"] == "hand"

        after = t / "b" / "seclists"
        after.parent.mkdir()
        (t / "a" / "seclists").rename(after)
        out, local = scan(t, after)

        assert sig in local, "moving a source must not lose the entry"
        assert local[sig]["paths"] == [str(after / "Discovery" / "common.txt")], \
            "the binding must follow the wordlist to its new path"
        assert local[sig]["intent"].startswith("Short directory names"), \
            "the intent is the paid-for work: a move must not cost it"
        assert local[sig]["intent_from"] == "hand", "a move must not downgrade provenance"
        assert "0 unqualified" in out and "0 no longer on disk" in out, out


def renamed():
    """Renaming the local root must not rewrite the collection.

    A collection is a set of wordlists with a common origin, and a category is a
    property of that collection rather than of the machine -- which is why both
    are committed. The directory we happen to mount SecLists at is a machine
    property, so the name we gave it locally must not overwrite either.
    """
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        sig, _ = seed(t, "a/seclists")
        scan(t, t / "a" / "seclists")

        (t / "a" / "seclists").rename(t / "a" / "sl")
        _, local = scan(t, t / "a" / "sl")

        assert local[sig]["collection"] == "seclists", \
            "the local directory name is not the collection's name"
        assert local[sig]["category"] == "Discovery", \
            "the category routes the entry to a model: a rename must not move it"


def partial():
    """A stranger never holds exactly our wordlists.

    The ones they lack must be reported and left in the catalog they received:
    describing one machine is not a licence to shrink the shared catalog to it.
    """
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        sig, _ = seed(t, "a/seclists")
        absent = "0" * 32
        cat = catalog.read(t / catalog.CATALOG)
        cat[absent] = {"sig": absent, "name": "rockyou.txt", "collection": "seclists",
                       "category": "Passwords", "intent": "Ten million leaked passwords.",
                       "intent_from": "harvested", "target": ["password"]}
        catalog.write(t / catalog.CATALOG, cat.values())

        out, local = scan(t, t / "a" / "seclists")

        assert sig in local, "the wordlist this disk does hold must be bound"
        assert absent not in local, "local.jsonl describes this disk and no other"
        assert "1 no longer on disk" in out, out
        kept = catalog.read(t / catalog.CATALOG)
        assert absent in kept and kept[absent]["intent_from"] == "harvested", \
            "a scan must not drop an entry the catalog describes but this disk lacks"


def exported():
    """The round trip: what a receiver exports is what a third machine imports.

    This is the whole claim. A catalog that only ever reads is of no use to
    anyone downstream; an export that carries this machine's paths, or that
    shrinks the catalog to this machine's disk, is worse than none.
    """
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        body, local_only = b"admin\nbackup\n", b"wp-admin\nwp-login.php\n"
        sig, common = seed(t, "a/seclists", body)
        # A wordlist this machine installed and the received catalog never described.
        (common.parent / "raft.txt").write_bytes(local_only)
        sig2 = hashlib.md5(local_only).hexdigest()
        absent = "0" * 32
        cat = catalog.read(t / catalog.CATALOG)
        cat[absent] = {"sig": absent, "name": "rockyou.txt", "collection": "seclists",
                       "category": "Passwords", "intent": "Ten million leaked passwords.",
                       "intent_from": "harvested", "target": ["password"]}
        catalog.write(t / catalog.CATALOG, cat.values())
        scan(t, t / "a" / "seclists")
        assert sig2 not in catalog.read(t / catalog.CATALOG), \
            "the scan must not publish to the shared catalog on its own"

        run(t, "--export")
        shared = catalog.read(t / catalog.CATALOG)

        assert sig2 in shared, "an export must carry what this machine added"
        assert absent in shared, \
            "an export is a merge: it must not shrink the catalog to this disk"
        for e in shared.values():
            assert not set(e) & set(catalog.LOCAL_ONLY), \
                f"{e['name']}: a shared catalog carries no path and no sample"

        # An export is shareable only if it is stable: a rescan and a second
        # export must not churn it, or every receiver sees a diff that carries
        # no information.
        before = (t / catalog.CATALOG).read_text()
        scan(t, t / "a" / "seclists")
        run(t, "--export")
        assert (t / catalog.CATALOG).read_text() == before, \
            "a rescan and re-export must not churn the shared catalog"

        # A third machine, same content, a path neither of the first two ever saw.
        with tempfile.TemporaryDirectory() as tmp3:
            t3 = Path(tmp3)
            third = t3 / "opt" / "seclists" / "Discovery"
            third.mkdir(parents=True)
            (third / "common.txt").write_bytes(body)
            (third / "raft.txt").write_bytes(local_only)
            catalog.write(t3 / catalog.CATALOG, shared.values())

            out, local = scan(t3, t3 / "opt" / "seclists")

            assert local[sig]["intent"].startswith("Short directory names"), \
                "the exported catalog must carry its intents to a machine we never saw"
            assert local[sig]["paths"] == [str(third / "common.txt")]
            assert local[sig2]["intent"] == "TODO", \
                "an entry exported unqualified stays qualifiable downstream"
            assert "1 unqualified" in out, out


def selftest():
    moved()
    renamed()
    partial()
    exported()
    print("portability ok")


if __name__ == "__main__":
    selftest()
