# 07: Qualify the whole catalog

**What to build:** every installed wordlist carries an intent an agent can act
on. This is the deliverable the project exists for: an agent on a mission stops
recalling paths from memory, and starts finding the payload lists and
tool-shipped lists it would never have looked for.

An operation rather than a code change. It runs the machinery the earlier
tickets built, with the routing the calibration chose.

**Blocked by:** 02, 03, 04, 06.

**Status:** ready-for-human

- [ ] Every entry carries an intent, or is listed as an explicit rejection with
      a reason.
- [ ] The distinctness gate passes without the threshold having been lowered to
      make it pass.
- [ ] The operator reads a random sample and accepts it. The spine of the
      project is these sentences; a run that passes the mechanical gates and
      still reads as interchangeable has failed.
- [ ] The shared catalog contains no absolute path and can be published as is.
- [ ] An agent, given only the selection skill and the local catalog, picks a
      defensible wordlist for a target it was not prompted about.

## Comments

Blocked on 06 and on spend. The machinery is in place and the free pass has run:
17 of 1,379 entries carry an intent harvested from documentation, 22 carry a
documented year, and 1,362 still read `intent: "TODO"`. `catalogue.jsonl` is
committed and carries no absolute path.

The rest is an operation for the operator: run `calibrate.py`, then `qualify.py`,
then read a random sample and accept it. The last two boxes are judgements that
cannot be self-certified, and the second of them — an agent picking a defensible
wordlist for an unprompted target — is the only test that matters.
