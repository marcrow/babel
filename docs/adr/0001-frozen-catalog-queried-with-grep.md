# Frozen catalog queried with grep, not a service

An agent on a mission needs to pick from roughly 1,200 entries. We keep the
catalog as a committed JSONL file, one entry per line, queried at mission time
with `rg` and `jq`. No server, no MCP, no process.

## Considered Options

**An MCP server** was the obvious shape, and we rejected it. The only one ever
written for this job, `sec-seclists-mcp`, drew zero stars and was archived in
June 2026. A server adds a lifecycle and a failure mode in exchange for
grepping a 1,200-line file.

**The catalog inside the skill** was rejected on arithmetic. The two existing
wordlist skills spend 4.5 KB and 11.4 KB to cover 30 and 80 paths; at that
ratio 1,200 entries run to roughly 45,000 tokens of context. The skill
therefore holds the method and the vocabulary, never the data.

**Live analysis at read time** was rejected because the content of a wordlist
does not change. Paying a model to re-read the same file on every query buys
nothing.

## Consequences

JSONL rather than JSON or Markdown is the load-bearing choice. One entry per
line means `grep` structurally cannot return more than what matched, so a query
costs the agent a handful of lines. Any format that nests entries inside a
document would have to be read whole in order to be filtered.

The catalog is editable by hand, which is required: intents will be wrong and
have to be corrected in place. Nothing regenerates them behind the operator's
back.
