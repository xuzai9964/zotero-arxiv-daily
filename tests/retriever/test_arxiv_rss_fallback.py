"""Recover metadata from RSS when the arXiv API rejects requests."""

import arxiv
import pytest
from copy import deepcopy

from zotero_arxiv_daily.retriever.arxiv_retriever import ArxivRetriever


@pytest.mark.parametrize("include_cross,debug", [(False, False), (True, False), (True, True)])
def test_http_406_uses_rss_metadata(config, mock_feedparser, monkeypatch, include_cross, debug):
    config.source.arxiv.include_cross_list = include_cross
    config.executor.debug = debug
    allowed = {"new", "cross"} if include_cross else {"new"}
    expected = [e for e in mock_feedparser.entries if e.arxiv_announce_type in allowed]
    if debug:
        expected = expected[:10]

    def rejected(self, search):
        raise arxiv.HTTPError("https://export.arxiv.org/api/query", 10, 406)

    monkeypatch.setattr(arxiv.Client, "results", rejected)
    papers = ArxivRetriever(config)._retrieve_raw_papers()
    assert len(papers) == len(expected)
    for paper, entry in zip(papers, expected):
        pid = entry.id.removeprefix("oai:arXiv.org:")
        assert paper.entry_id == f"https://arxiv.org/abs/{pid}"
        assert paper.pdf_url == f"https://arxiv.org/pdf/{pid}"
        assert paper.source_url() == f"https://arxiv.org/src/{pid}"
        assert paper.title == entry.title
        assert paper.summary == entry.summary.partition("Abstract:")[2].strip()
        assert [a.name for a in paper.authors] == entry.author.split(", ")


def test_other_http_errors_remain_visible(config, mock_feedparser, monkeypatch):
    def rejected(self, search):
        raise arxiv.HTTPError("https://export.arxiv.org/api/query", 10, 500)

    monkeypatch.setattr(arxiv.Client, "results", rejected)
    with pytest.raises(arxiv.HTTPError) as exc:
        ArxivRetriever(config)._retrieve_raw_papers()
    assert exc.value.status == 500


def test_406_after_successful_batch_preserves_results(config, mock_feedparser, monkeypatch):
    template = next(e for e in mock_feedparser.entries if e.arxiv_announce_type == "new")
    mock_feedparser.entries = [deepcopy(template) for _ in range(25)]
    for index, entry in enumerate(mock_feedparser.entries):
        entry.id = f"oai:arXiv.org:2609.{index:05d}v1"
    first_batch = [object() for _ in range(20)]
    calls = []

    def results(self, search):
        calls.append(search.id_list)
        if len(calls) == 1:
            return iter(first_batch)
        raise arxiv.HTTPError("https://export.arxiv.org/api/query", 10, 406)

    monkeypatch.setattr(arxiv.Client, "results", results)
    monkeypatch.setattr("zotero_arxiv_daily.retriever.arxiv_retriever.sleep", lambda _: None)
    papers = ArxivRetriever(config)._retrieve_raw_papers()
    assert papers[:20] == first_batch
    assert len(papers) == 25
    assert [p.entry_id for p in papers[20:]] == [
        f"https://arxiv.org/abs/2609.{index:05d}v1" for index in range(20, 25)
    ]
    assert len(calls) == 2
