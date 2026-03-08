from .protocol import Paper
from datetime import datetime
import os
import re
from loguru import logger


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = name.strip('. ')
    if len(name) > 150:
        name = name[:150].strip()
    return name


def render_paper_note(paper: Paper) -> str:
    authors = paper.authors or []
    if len(authors) <= 5:
        author_str = ', '.join(authors)
    else:
        author_str = ', '.join(authors[:3] + ['...'] + authors[-2:])

    affiliations = ''
    if paper.affiliations:
        affs = paper.affiliations[:5]
        affiliations = ', '.join(affs)
        if len(paper.affiliations) > 5:
            affiliations += ', ...'

    score = round(paper.score, 1) if paper.score is not None else 0
    tags_yaml = '\n'.join(f'  - {t}' for t in ['arxiv-daily', paper.source])

    lines = [
        '---',
        f'title: "{paper.title}"',
        f'authors: "{author_str}"',
        f'affiliations: "{affiliations}"',
        f'relevance: {score}',
        f'source: {paper.source}',
        f'url: {paper.url}',
        f'pdf: {paper.pdf_url or ""}',
        f'date: {datetime.now().strftime("%Y-%m-%d")}',
        f'tags:',
        tags_yaml,
        '---',
        '',
        f'# {paper.title}',
        '',
        f'**Authors:** {author_str}',
    ]

    if affiliations:
        lines.append(f'**Affiliations:** {affiliations}')

    lines.extend([
        f'**Relevance:** {score}/10',
        '',
        '## TLDR',
        '',
        paper.tldr or paper.abstract or 'No summary available.',
        '',
        '## Abstract',
        '',
        paper.abstract or 'No abstract available.',
        '',
        f'[PDF]({paper.pdf_url})' if paper.pdf_url else '',
    ])

    return '\n'.join(lines)


def render_index_note(papers: list[Paper], date_str: str) -> str:
    lines = [
        '---',
        f'date: {date_str}',
        'tags:',
        '  - arxiv-daily',
        '  - index',
        '---',
        '',
        f'# Arxiv Daily — {date_str}',
        '',
        f'**{len(papers)} papers** with relevance > threshold.',
        '',
        '| Score | Title |',
        '|-------|-------|',
    ]

    for p in papers:
        score = round(p.score, 1) if p.score is not None else 0
        safe_title = sanitize_filename(p.title)
        lines.append(f'| {score} | [[{safe_title}]] |')

    return '\n'.join(lines)


def output_obsidian_notes(papers: list[Paper], output_dir: str, min_score: float = 3.0) -> str:
    filtered = [p for p in papers if p.score is not None and p.score >= min_score]
    filtered = sorted(filtered, key=lambda x: x.score, reverse=True)

    if len(filtered) == 0:
        logger.info(f"No papers with score >= {min_score}. Skipping obsidian output.")
        return output_dir

    date_str = datetime.now().strftime("%Y.%m.%d")
    folder_name = f"{date_str}-arxiv"
    folder_path = os.path.join(output_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for p in filtered:
        filename = sanitize_filename(p.title) + '.md'
        filepath = os.path.join(folder_path, filename)
        content = render_paper_note(p)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    index_content = render_index_note(filtered, date_str)
    index_path = os.path.join(folder_path, f'{folder_name}.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)

    logger.info(f"Written {len(filtered)} obsidian notes to {folder_path}")
    return folder_path
