import os
import tempfile
from zotero_arxiv_daily.protocol import Paper
from zotero_arxiv_daily.construct_obsidian import (
    sanitize_filename,
    render_paper_note,
    render_index_note,
    output_obsidian_notes,
)


def make_paper(title="Test Paper", score=5.0):
    return Paper(
        source="arxiv",
        title=title,
        authors=["Alice", "Bob", "Charlie"],
        abstract="This is a test abstract.",
        url="https://arxiv.org/abs/1234.56789",
        pdf_url="https://arxiv.org/pdf/1234.56789",
        tldr="A test paper about testing.",
        affiliations=["MIT", "Stanford"],
        score=score,
    )


def test_sanitize_filename():
    assert sanitize_filename('Hello: World?') == 'Hello World'
    assert sanitize_filename('A' * 200) == 'A' * 150


def test_render_paper_note():
    paper = make_paper()
    note = render_paper_note(paper)
    assert '---' in note
    assert 'Test Paper' in note
    assert 'Alice, Bob, Charlie' in note
    assert 'relevance: 5.0' in note
    assert 'A test paper about testing.' in note


def test_render_index_note():
    papers = [make_paper("Paper A", 7.0), make_paper("Paper B", 4.5)]
    index = render_index_note(papers, "2026.03.08")
    assert '2026.03.08' in index
    assert '2 papers' in index
    assert '[[Paper A]]' in index
    assert '[[Paper B]]' in index


def test_output_obsidian_notes():
    papers = [
        make_paper("High Score Paper", 5.0),
        make_paper("Low Score Paper", 1.0),
        make_paper("Medium Score Paper", 3.5),
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        output_obsidian_notes(papers, tmpdir, min_score=3.0)
        # Should have created a dated folder
        folders = os.listdir(tmpdir)
        assert len(folders) == 1
        folder = folders[0]
        assert folder.endswith('-arxiv')
        files = os.listdir(os.path.join(tmpdir, folder))
        # 2 papers (score >= 3) + 1 index note = 3 files
        assert len(files) == 3
        assert 'High Score Paper.md' in files
        assert 'Medium Score Paper.md' in files


def test_output_obsidian_notes_empty():
    papers = [make_paper("Low Paper", 1.0)]
    with tempfile.TemporaryDirectory() as tmpdir:
        output_obsidian_notes(papers, tmpdir, min_score=3.0)
        # No folder should be created
        assert len(os.listdir(tmpdir)) == 0
