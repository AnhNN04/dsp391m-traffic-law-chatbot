import re
import json
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# --- CẤU HÌNH ---
MD_FIXED_DIR = Path(r'C:\DSP\convert_to_md\data\proceed')
CHUNK_DIR = Path(r'C:\DSP\convert_to_md\data\chunks')
CHUNK_VERSION = "v5"

# Regex phân tích cấu trúc văn bản
CHAPTER_PATTERN = re.compile(r"^[\*]*(Chương\s+[IVXLCDM\d]+)[\*]*$", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^[\*]*(Mục\s+\d+)\.?\s*(.*?)[\*]*$", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^\*\*(Điều\s+(\d+)\.?.*?)\*\*")
CLAUSE_PATTERN  = re.compile(r"^(\d+)\.\s+(.*)$")
POINT_PATTERN   = re.compile(r"^([a-zđĐ])[\.\)]\s+(.*)$", re.IGNORECASE)

# Regex nhận dạng loại văn bản (từ dòng **LUẬT**, **THÔNG TƯ**, ...)
LAW_TYPE_PATTERNS = [
    (re.compile(r"^\*\*LUẬT\*\*$", re.IGNORECASE),                "Luật"),
    (re.compile(r"^\*\*NGHỊ QUYẾT\*\*$", re.IGNORECASE),          "Nghị quyết"),
    (re.compile(r"^\*\*NGHỊ ĐỊNH\*\*$", re.IGNORECASE),           "Nghị định"),
    (re.compile(r"^\*\*THÔNG TƯ\*\*$", re.IGNORECASE),            "Thông tư"),
    (re.compile(r"^\*\*THÔNG TƯ LIÊN TỊCH\*\*$", re.IGNORECASE), "Thông tư liên tịch"),
    (re.compile(r"^\*\*QUYẾT ĐỊNH\*\*$", re.IGNORECASE),          "Quyết định"),
    (re.compile(r"^\*\*CHỈ THỊ\*\*$", re.IGNORECASE),             "Chỉ thị"),
    (re.compile(r"^\*\*PHÁP LỆNH\*\*$", re.IGNORECASE),           "Pháp lệnh"),
    (re.compile(r"^\*\*HIẾN PHÁP\*\*$", re.IGNORECASE),           "Hiến pháp"),
]

# Regex nhận dạng điểm kết thúc văn bản (phần boilerplate hành chính)
END_OF_LAW_PATTERNS = [
    # Nơi nhận (nhiều format)
    re.compile(r"^_?\*?\*?Nơi nhận:\*?\*?_?$", re.IGNORECASE),
    re.compile(r"^\*?\*?Nơi nhận:\*?\*?"),
    re.compile(r"^Nơi nhận:"),
    # Ký tên (plain và bold)
    re.compile(r"^\*?\*?TM\.\s*(CHÍNH PHỦ|ỦY BAN|BỘ)", re.IGNORECASE),
    re.compile(r"^\*?\*?KT\.\s*(BỘ TRƯỞNG|THỨ TRƯỞNG|THỦ TƯỚNG|TỔNG CỤC TRƯỞNG|CỤC TRƯỞNG)", re.IGNORECASE),
    re.compile(r"^\*?\*?(BỘ TRƯỞNG|THỨ TRƯỞNG|THỦ TƯỚNG|TỔNG CỤC TRƯỞNG|CỤC TRƯỞNG)\*?\*?$", re.IGNORECASE),
    re.compile(r"^FILE ĐƯỢC ĐÍNH KÈM THEO VĂN BẢN", re.IGNORECASE),
    re.compile(r"^\*?\*?PHỤ LỤC", re.IGNORECASE),
    re.compile(r"^PHỤ LỤC\s*(I|II|III|IV|V|\d+)?", re.IGNORECASE),
]

# Pattern bảng markdown (table separator)
TABLE_SEPARATOR_PATTERN = re.compile(r"^\|[-\s|]+\|$")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("**", "").replace("_", "")
    return re.sub(r"\s+", " ", text).strip()


def is_end_of_law(line: str) -> bool:
    """Kiểm tra xem dòng có phải điểm kết thúc nội dung pháp lý hay không."""
    stripped = line.strip()
    for pattern in END_OF_LAW_PATTERNS:
        if pattern.match(stripped):
            return True
    # Bảng markdown dày đặc (xuất hiện | padding |)
    if TABLE_SEPARATOR_PATTERN.match(stripped):
        return True
    return False


def extract_law_metadata(lines: List[str]) -> Tuple[str, str]:
    """
    Trích xuất loại văn bản và tên văn bản từ phần header của file markdown.
    Scan tối đa 50 dòng đầu để tìm pattern **LUẬT**, **THÔNG TƯ**, ...
    Dòng tiếp theo (không rỗng, không phải căn cứ/chú thích) là tên văn bản.

    Returns:
        (law_type, law_name) - ví dụ ("Luật", "TRẬT TỰ, AN TOÀN GIAO THÔNG ĐƯỜNG BỘ")
    """
    scan_limit = min(60, len(lines))

    for i, line in enumerate(lines[:scan_limit]):
        stripped = line.strip()
        for pattern, law_type in LAW_TYPE_PATTERNS:
            if pattern.match(stripped):
                # Tìm tên văn bản: lấy tất cả các dòng tiếp theo (không rỗng) đến khi
                # gặp dòng bắt đầu bằng _Căn cứ hoặc _Quốc hội hoặc _Chính phủ
                name_parts = []
                j = i + 1
                while j < scan_limit:
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    # Dừng khi gặp phần căn cứ hoặc tiêu đề khác
                    if (next_line.startswith("_Căn cứ") or
                            next_line.startswith("_Quốc hội") or
                            next_line.startswith("_Chính phủ") or
                            next_line.startswith("_Bộ trưởng") or
                            next_line.startswith("_Theo đề nghị") or
                            CHAPTER_PATTERN.match(next_line) or
                            ARTICLE_PATTERN.match(next_line)):
                        break
                    # Bỏ qua các dòng số văn bản (VD: "Số: 17/2026/NĐ-CP ...")
                    if re.match(r"^Số:\s+\d+", next_line):
                        j += 1
                        continue
                    # Bỏ qua dòng là tên cơ quan ban hành (thường all caps ngắn, bold)
                    clean = clean_text(next_line)
                    if not clean:
                        j += 1
                        continue
                    # Bỏ qua dòng bold ngắn (ví dụ: "BỘ GIAO THÔNG VẬN TẢI", "CHÍNH PHỦ")
                    if next_line.startswith("**") and next_line.endswith("**") and len(clean) <= 40 and not name_parts:
                        j += 1
                        continue
                    name_parts.append(clean)
                    j += 1

                law_name = " ".join(name_parts).strip()
                # Fallback nếu không tìm được tên
                if not law_name:
                    law_name = law_type.upper()
                return law_type, law_name

    # Fallback: suy diễn từ tên file
    return "Văn bản pháp luật", ""


@dataclass
class ParsingState:
    chapter_id: Optional[str] = None
    chapter_name: Optional[str] = None
    section: Optional[str] = None
    article: Optional[str] = None
    article_id: Optional[str] = None
    clause_id: Optional[str] = None
    clause_text: List[str] = field(default_factory=list)
    clause_points: List[str] = field(default_factory=list)
    article_has_clause: bool = False
    article_text: List[str] = field(default_factory=list)
    preamble: List[str] = field(default_factory=list)
    expect_chapter_name: bool = False


def build_chunk(*, law_id: str, law_type: str, law_name: str,
                state: ParsingState, clause_id: Optional[str], content: str) -> Dict:
    """Xây dựng một chunk JSON với embed_content phân cấp rõ ràng."""
    # Xây dựng phân cấp ngữ nghĩa bằng dấu " > "
    hierarchy = [f"{law_type}: {law_name}"]
    if state.chapter_id:
        chap_label = f"{state.chapter_id}: {state.chapter_name}" if state.chapter_name else state.chapter_id
        hierarchy.append(chap_label)
    if state.section:
        hierarchy.append(state.section)
    if state.article:
        hierarchy.append(state.article)
    if clause_id and clause_id != "Căn cứ":
        hierarchy.append(f"Khoản {clause_id}")

    hierarchy.append(content)
    embed_content = " > ".join([p for p in hierarchy if p])

    return {
        "law_id": law_id,
        "type": law_type,
        "law_name": law_name,
        "chapter_id": state.chapter_id,
        "chapter_name": state.chapter_name,
        "section": state.section,
        "article_id": state.article_id,
        "article": state.article,
        "clause": clause_id,
        "content": content,
        "embed_content": embed_content,
    }


def flush_clause(state: ParsingState, law_id: str, law_type: str,
                 law_name: str, chunks: List[Dict]) -> None:
    """Đẩy clause hiện tại vào danh sách chunks."""
    if not state.clause_id:
        return
    # Nối text khoản + các điểm
    text = " ".join(state.clause_text)
    if state.clause_points:
        text += " " + " ".join(state.clause_points)
    content = clean_text(text)
    if content:
        chunks.append(build_chunk(
            law_id=law_id, law_type=law_type, law_name=law_name,
            state=state, clause_id=state.clause_id, content=content
        ))
    # Reset clause state
    state.clause_id = None
    state.clause_text = []
    state.clause_points = []


def flush_article_only(state: ParsingState, law_id: str, law_type: str,
                       law_name: str, chunks: List[Dict]) -> None:
    """Đẩy nội dung Điều không có khoản vào danh sách chunks."""
    if not state.article_text:
        return
    content = clean_text(" ".join(state.article_text))
    if content:
        chunks.append(build_chunk(
            law_id=law_id, law_type=law_type, law_name=law_name,
            state=state, clause_id=None, content=content
        ))
    state.article_text.clear()


def reset_article_state(state: ParsingState) -> None:
    """Reset toàn bộ state liên quan đến Điều hiện tại."""
    state.article = None
    state.article_id = None
    state.article_has_clause = False
    state.article_text = []
    state.clause_id = None
    state.clause_text = []
    state.clause_points = []


def chunk_law_markdown(md_path: Path) -> List[Dict]:
    """Parse một file markdown đã fix và trả về danh sách chunks."""
    # law_id = tên file bỏ _fix (dùng _fix để replace chính xác)
    law_id = md_path.stem.replace("_fix", "")

    raw_lines = md_path.read_text(encoding="utf-8").splitlines()
    # Bỏ dòng trống đầu/cuối, giữ lại cấu trúc để scan header
    lines = [l.strip() for l in raw_lines]

    # Trích xuất metadata loại văn bản và tên từ header file
    law_type, law_name = extract_law_metadata(lines)

    # Lọc dòng rỗng để parse (nhưng giữ ngữ cảnh liên tục)
    non_empty_lines = [l for l in lines if l]

    chunks: List[Dict] = []
    state = ParsingState()
    stopped = False  # cờ dừng khi gặp cuối văn bản pháp lý

    for line in non_empty_lines:
        # Kiểm tra cuối văn bản
        if is_end_of_law(line):
            # Flush state cuối cùng trước khi dừng
            if state.article:
                if state.article_has_clause:
                    flush_clause(state, law_id, law_type, law_name, chunks)
                else:
                    flush_article_only(state, law_id, law_type, law_name, chunks)
            stopped = True
            break

        # --- Chương ---
        m_chap = CHAPTER_PATTERN.match(line)
        if m_chap:
            # Flush điều đang xử lý
            if state.article:
                if state.article_has_clause:
                    flush_clause(state, law_id, law_type, law_name, chunks)
                else:
                    flush_article_only(state, law_id, law_type, law_name, chunks)
                reset_article_state(state)
            state.chapter_id = clean_text(m_chap.group(1))
            state.expect_chapter_name = True
            state.section = None
            continue

        # --- Tên chương (dòng ngay sau Chương ...) ---
        if state.expect_chapter_name:
            if not SECTION_PATTERN.match(line) and not ARTICLE_PATTERN.match(line):
                state.chapter_name = clean_text(line)
                state.expect_chapter_name = False
                continue
            state.expect_chapter_name = False

        # --- Mục ---
        m_sec = SECTION_PATTERN.match(line)
        if m_sec:
            state.section = clean_text(line)
            continue

        # --- Điều ---
        m_art = ARTICLE_PATTERN.match(line)
        if m_art:
            # Flush điều trước
            if state.article:
                if state.article_has_clause:
                    flush_clause(state, law_id, law_type, law_name, chunks)
                else:
                    flush_article_only(state, law_id, law_type, law_name, chunks)
            # Reset toàn bộ state của điều cũ trước khi bắt đầu điều mới
            reset_article_state(state)
            state.article = clean_text(m_art.group(1))
            state.article_id = m_art.group(2)
            continue

        # --- Khoản ---
        m_clause = CLAUSE_PATTERN.match(line)
        if m_clause and state.article:
            flush_clause(state, law_id, law_type, law_name, chunks)
            state.article_has_clause = True
            state.clause_id = m_clause.group(1)
            clause_text_start = clean_text(m_clause.group(2))
            state.clause_text = [clause_text_start] if clause_text_start else []
            continue

        # --- Điểm ---
        m_point = POINT_PATTERN.match(line)
        if m_point and state.clause_id:
            state.clause_points.append(f"Điểm {m_point.group(1)}. {clean_text(m_point.group(2))}")
            continue

        # --- Nội dung thông thường ---
        if state.article:
            # Bỏ qua các dòng là toàn bộ bảng markdown (bắt đầu bằng |)
            if line.startswith("|"):
                continue
            if state.clause_id:
                state.clause_text.append(line)
            else:
                state.article_text.append(line)

    # Flush phần cuối nếu chưa bị dừng
    if not stopped and state.article:
        if state.article_has_clause:
            flush_clause(state, law_id, law_type, law_name, chunks)
        else:
            flush_article_only(state, law_id, law_type, law_name, chunks)

    return chunks


def main():
    print(f"Đang quét thư mục: {MD_FIXED_DIR}")

    if not MD_FIXED_DIR.exists():
        print("❌ LỖI: Thư mục đầu vào không tồn tại!")
        return

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(MD_FIXED_DIR.glob("*_fix.md"))
    print(f"Tìm thấy {len(md_files)} file .md\n")

    total_chunks = 0
    errors = []

    for md_path in md_files:
        print(f"--- Đang xử lý: {md_path.name} ---")
        try:
            chunks = chunk_law_markdown(md_path)
        except Exception as e:
            print(f"  ❌ Lỗi khi xử lý: {e}")
            errors.append(md_path.name)
            continue

        if not chunks:
            print(f"  ⚠️  Cảnh báo: Không trích xuất được chunk nào. Kiểm tra lại Regex!")
            errors.append(md_path.name)
            continue

        out_path = CHUNK_DIR / f"{md_path.stem}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        law_id   = chunks[0].get("law_id", "?")
        law_type = chunks[0].get("type", "?")
        print(f"  ✅ Xong: {len(chunks)} chunks | law_id={law_id} | type={law_type}")
        print(f"     → {out_path}")
        total_chunks += len(chunks)

    print(f"\n{'='*60}")
    print(f"HOÀN TẤT: {len(md_files) - len(errors)}/{len(md_files)} file thành công")
    print(f"Tổng số chunks: {total_chunks}")
    if errors:
        print(f"❌ Lỗi / cảnh báo: {errors}")


if __name__ == "__main__":
    main()