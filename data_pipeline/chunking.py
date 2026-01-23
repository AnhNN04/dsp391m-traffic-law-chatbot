import re
import json
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import tiktoken

from config import MD_FIXED_DIR, CHUNK_DIR, CHUNK_VERSION

LAW_PATTERN = re.compile(r"^#\s+\*\*(.+?)\*\*")
CHAPTER_OR_SECTION_PATTERN = re.compile(r"^##\s+\*\*(.+?)\*\*")
ARTICLE_PATTERN = re.compile(r"^###\s+\*\*(Điều\s+(\d+)\.?.*?)\*\*")

CLAUSE_PATTERN = re.compile(r"^(\d+)\.\s+(.*)$")
POINT_PATTERN = re.compile(r"^([a-z])\.\s+(.*)$")

ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))

def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def clean_text(text: str) -> str:
    return normalize_whitespace(normalize_unicode(text))

def normalize_for_embedding(text: str) -> str:
    return normalize_whitespace(normalize_unicode(text).lower())

def parse_law_id_from_filename(path: Path) -> str:
    name = path.stem.upper()
    if "LTTATGTDB" in name:
        return "LTTATGTDB"
    if "LDB" in name:
        return "LDB"
    return name

def build_detail_content(
    law_name: str,
    chapter: Optional[str],
    section: Optional[str],
    article: Optional[str],
    clause: Optional[str],
    content: str,
) -> str:
    parts = []
    if law_name:
        parts.append(law_name)
    if chapter:
        parts.append(chapter)
    if section:
        parts.append(section)
    if article:
        parts.append(article)
    if clause:
        parts.append(f"Khoản {clause}")
    parts.append(content)
    return ". ".join(parts)

@dataclass
class ParsingState:
    law_name: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    article: Optional[str] = None
    article_id: Optional[str] = None

    clause_id: Optional[str] = None
    clause_text: List[str] = field(default_factory=list)
    clause_points: List[str] = field(default_factory=list)

    article_has_clause: bool = False
    article_text: List[str] = field(default_factory=list)

def build_chunk(
    *,
    law_id: str,
    state: ParsingState,
    clause_id: Optional[str],
    content: str,
) -> Dict:
    detail = build_detail_content(
        state.law_name,
        state.chapter,
        state.section,
        state.article,
        clause_id,
        content,
    )

    return {
        "law_id": law_id,
        "article_id": state.article_id,
        "clause_id": clause_id,
        "token_count": count_tokens(normalize_for_embedding(detail)),
        "Tên-Luật": state.law_name,
        "Chương": state.chapter,
        "Mục": state.section,
        "Điều": state.article,
        "Khoản": clause_id,
        "Nội-Dung": content,
        "embed_content": detail,
    }

def flush_clause(state: ParsingState, law_id: str, chunks: list):
    if not state.clause_id:
        return

    parts = []
    if state.clause_text:
        parts.append(" ".join(state.clause_text))
    parts.extend(state.clause_points)

    chunks.append(
        build_chunk(
            law_id=law_id,
            state=state,
            clause_id=state.clause_id,
            content=clean_text(" ".join(parts)),
        )
    )

    state.clause_id = None
    state.clause_text.clear()
    state.clause_points.clear()

def flush_article_if_no_clause(state: ParsingState, law_id: str, chunks: list):
    if not state.article_text:
        return

    chunks.append(
        build_chunk(
            law_id=law_id,
            state=state,
            clause_id=None,
            content=clean_text(" ".join(state.article_text)),
        )
    )

    state.article_text.clear()

def handle_law_and_structure(line: str, state: ParsingState) -> bool:
    m = LAW_PATTERN.match(line)
    if m:
        state.law_name = clean_text(m.group(1))
        return True

    m = CHAPTER_OR_SECTION_PATTERN.match(line)
    if m:
        title = clean_text(m.group(1))
        if title.lower().startswith("chương"):
            state.chapter = title
            state.section = None
        elif title.lower().startswith("mục"):
            state.section = title
        return True

    return False

def handle_article(line: str, state: ParsingState, law_id: str, chunks: list) -> bool:
    m = ARTICLE_PATTERN.match(line)
    if not m:
        return False

    if state.article:
        if state.article_has_clause:
            flush_clause(state, law_id, chunks)
        else:
            flush_article_if_no_clause(state, law_id, chunks)

    state.article = clean_text(m.group(1))
    state.article_id = m.group(2)
    state.article_has_clause = False
    state.article_text.clear()
    state.clause_id = None
    state.clause_text.clear()
    state.clause_points.clear()

    return True

def handle_clause(line: str, state: ParsingState, law_id: str, chunks: list) -> bool:
    m = CLAUSE_PATTERN.match(line)
    if not m:
        return False

    state.article_has_clause = True
    flush_clause(state, law_id, chunks)

    state.clause_id = m.group(1)
    state.clause_text = [clean_text(m.group(2))]
    state.clause_points.clear()

    return True

def handle_point(line: str, state: ParsingState) -> bool:
    m = POINT_PATTERN.match(line)
    if m and state.clause_id:
        state.clause_points.append(
            f"Điểm {m.group(1)}. {clean_text(m.group(2))}"
        )
        return True
    return False

def handle_plain_text(line: str, state: ParsingState):
    if state.clause_id:
        state.clause_text.append(clean_text(line))
    else:
        state.article_text.append(clean_text(line))

def chunk_law_markdown(md_path: Path) -> List[Dict]:
    law_id = parse_law_id_from_filename(md_path)

    lines = [
        line.strip()
        for line in md_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    chunks = []
    state = ParsingState()

    for line in lines:
        if handle_law_and_structure(line, state):
            continue
        if handle_article(line, state, law_id, chunks):
            continue
        if handle_clause(line, state, law_id, chunks):
            continue
        if handle_point(line, state):
            continue
        handle_plain_text(line, state)

    if state.article:
        if state.article_has_clause:
            flush_clause(state, law_id, chunks)
        else:
            flush_article_if_no_clause(state, law_id, chunks)

    return chunks

def main():
    if not MD_FIXED_DIR.exists():
        raise RuntimeError(f"Input dir not found: {MD_FIXED_DIR}")

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(MD_FIXED_DIR.glob("*.md"))
    if not md_files:
        raise RuntimeError("No markdown files to chunk")

    for md_path in md_files:
        out_path = CHUNK_DIR / f"{md_path.stem}-{CHUNK_VERSION}.json"

        chunks = chunk_law_markdown(md_path)
        out_path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"[OK] {md_path.name} → {out_path.name} | chunks={len(chunks)}")


if __name__ == "__main__":
    main()
