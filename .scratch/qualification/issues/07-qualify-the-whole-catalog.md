# 07: Qualify the whole catalog

**What to build:** every installed wordlist carries an intent an agent can act
on. This is the deliverable the project exists for: an agent on a mission stops
recalling paths from memory, and starts finding the payload lists and
tool-shipped lists it would never have looked for.

An operation rather than a code change. It runs the machinery the earlier
tickets built, with the routing the calibration chose.

**Blocked by:** 02, 03, 04, 06.

**Status:** done

- [x] Every entry carries an intent, or is listed as an explicit rejection with
      a reason.
- [x] The distinctness gate passes without the threshold having been lowered to
      make it pass.
- [x] The operator reads a random sample and accepts it. The spine of the
      project is these sentences; a run that passes the mechanical gates and
      still reads as interchangeable has failed.
- [x] The shared catalog contains no absolute path and can be published as is.
- [x] An agent, given only the selection skill and the local catalog, picks a
      defensible wordlist for a target it was not prompted about.

## Comments

**Run, by the operator, family by family on the subscription.** The catalog now
holds **1,373 entries, every one of them qualified, and 1,373 distinct intents** —
ronin-wordlists scores 0.019 on the same measure. 1,356 intents came from a
model, 11 were written by hand, 6 were harvested from a README. The distinctness
gate passed without the threshold being touched, `catalogue.jsonl` carries no
absolute path, and nothing is left tagged for review.

Spot-checked against the files themselves rather than for plausibility, which is
the check that matters: `actions.txt` is described as "224 verbs in both lowercase
and title case merged together, unordered" and the file is exactly 224 lines of
`accelerate`/`Accelerate` pairs; `hu.txt` as "Hungarian profanities with inflected
forms" and it reads `balfasz`, `balfaszok`, `balfaszokat`; the OpenLDAP class list
holds `account`, `alias`, `applicationEntity`. The numbers in the sentences are
right too — 3,807 payloads for 3,807 lines, 854 variants for 854.

**Four defects the analysis found, all in our own code or data.**

1. **A rescan silently destroyed `kind` on 61 entries.** The scan carries a fixed
   list of axes forward from the catalog and `kind` was never added to it, so a
   walk erased work a model had been paid for, without a word. The list is now
   `catalog.QUALIFIED`, named, in the shared module, and the self-check asserts
   every model-written axis is in it.
2. **An entry a model had looked at was re-sent on every pass.** A model-written
   intent with no target, which is the honest answer for a generator script, did
   not count as settled, so each pass paid for it again and re-tagged it. Now an
   intent plus either a target, a kind, or a model's own signature settles it.
3. **Ten web shells came back blank.** The model would not describe live backdoor
   code — obfuscated PHP shells, a JSP one-liner, the Vtiger plugin — so those ten
   are hand-written with `intent_from: hand`, which no model will overwrite. This
   is the mechanism ADR 0001 exists for, used for the first time in earnest.
4. **`word` reached 190 uses, 132 of them alone.** 69 are honest lexicons under
   `Miscellaneous`; eight were flat errors, a surname list under `Usernames/`
   whose target is `username`, and those are fixed. The rest, mostly the Dutch
   corpora, are defensible as lexicons and remain reachable by `language` and by
   free text, but `word` is the axis value to watch.

**Known and accepted.** 250 entries name no technology, so the skill now says to
read a missing `tech` as generic and to filter tech to rule one out rather than
require one. Three entries carry neither target nor kind. Packaging files that
are not wordlists at all — LICENCE, ReadMe.txt, Makefile, CREDITS, GPL — are now
excluded by the scan rather than described.

**The last box is the operator's and is not ticked by me.** `qualify.py --read 25`
prints a random sample for exactly that.

**The operator has read a random sample and accepted it.** That was the box no
measurement here could tick: a run can pass every mechanical gate and still read
as interchangeable, and only someone who knows the missions can say otherwise.
