# Deep web research

`milyonus research` turns a question into a **cited report**: it plans
sub-queries, searches the web, reads several sources, and synthesizes an answer
that cites `[n]` each source.

```bash
milyonus research "Who introduced the Model Context Protocol and when?"
milyonus research "compare vector databases for RAG" --sources 8 --subqueries 4
```

The agent can also call `web_search` and `deep_research` as tools during a
conversation.

## How it works

1. **Plan** — the model breaks the question into focused sub-queries.
2. **Search** — each sub-query is searched; unique URLs are collected.
3. **Read** — top sources are fetched (SSRF-guarded, deduped, HTML stripped to
   text, truncated per source).
4. **Synthesize** — the model writes a thorough answer, citing `[n]` each source,
   and flags where sources are thin or disagree.

Bounds (`--subqueries`, `--sources`, per-source length) keep context and cost in
check.

## Search providers

Keyless by default, pluggable when a key is present:

| Provider | Enabled by | Notes |
|---|---|---|
| **DuckDuckGo** | *(default, no key)* | Works out of the box |
| **Tavily** | `TAVILY_API_KEY` | LLM-oriented search |
| **Brave** | `BRAVE_API_KEY` | Brave Search API |

Set a key in `~/.milyonus/.env` to upgrade automatically.
