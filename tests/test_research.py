"""Deep research: DDG parsing, plan→search→read→synthesize with citations."""

from collections.abc import AsyncIterator

from milyonus.providers.base import CompletionRequest, StreamEvent, Usage
from milyonus.research.deep import deep_research
from milyonus.research.search import SearchResult, parse_ddg_html

DDG_HTML = """
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=x">First Result</a>
  <a class="result__snippet" href="x">snippet one about the topic</a>
</div>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fb">Second Result</a>
  <a class="result__snippet" href="x">snippet two</a>
</div>
"""


def test_parse_ddg_unwraps_urls():
    results = parse_ddg_html(DDG_HTML)
    assert len(results) == 2
    assert results[0].url == "https://example.com/a"
    assert results[0].title == "First Result"
    assert "snippet one" in results[0].snippet
    assert results[1].url == "https://example.org/b"


class ScriptedProvider:
    """Returns a plan (JSON) first, then a synthesized answer."""

    name = "fake"
    model = "fake"

    def __init__(self):
        self._calls = 0

    async def stream(self, req: CompletionRequest) -> AsyncIterator[StreamEvent]:
        self._calls += 1
        if self._calls == 1:  # plan
            text = '["subquery one", "subquery two"]'
        else:  # synthesis
            text = "The answer draws on both sources [1][2]."
        yield StreamEvent(kind="text", delta=text)
        yield StreamEvent(kind="usage", usage=Usage(input_tokens=10, output_tokens=5))
        yield StreamEvent(kind="done", stop_reason="end_turn")


async def test_deep_research_pipeline():
    async def fake_search(q, k):
        return [
            SearchResult("Doc A", "https://a.example/x", "about x"),
            SearchResult("Doc B", "https://b.example/y", "about y"),
        ]

    async def fake_fetch(url):
        return f"full text of {url}"

    report = await deep_research(
        "what is x?",
        provider=ScriptedProvider(),
        search_fn=fake_search,
        fetch_fn=fake_fetch,
        max_sources=4,
    )
    assert "[1]" in report.answer
    assert len(report.sources) == 2  # deduped across sub-queries
    rendered = report.render()
    assert "Sources:" in rendered and "a.example" in rendered


async def test_deep_research_no_sources():
    async def empty_search(q, k):
        return []

    report = await deep_research("obscure", provider=ScriptedProvider(), search_fn=empty_search)
    assert "No sources" in report.answer
