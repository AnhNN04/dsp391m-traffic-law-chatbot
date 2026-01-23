import re
from pathlib import Path

from config import MD_RAW_DIR, MD_FIXED_DIR, FIX_VERSION

END_SENTENCE_CHARS = (".", ":", ";", "!", "?")
VIETNAMESE_LETTER = r"a-zA-ZÀ-ỹĐđ"

def is_special_line(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith(("#", "-", "*", "•", ">"))
        or stripped.startswith("```")
        or stripped == ""
    )

def is_cong_bao_line(line: str) -> bool:
    upper = line.upper()
    return "CÔNG BÁO" in upper and "/SỐ" in upper and "/NGÀY" in upper

def normalize_alpha_bullet(line: str) -> str:
    """
    Convert:
        a) -> a.
        đ) -> đ.
        Đ) -> Đ.
    """
    pattern = rf"^([{VIETNAMESE_LETTER}])\)\s+"
    return re.sub(pattern, r"\1. ", line)

def fix_broken_lines(md_path: Path) -> str:
    if not md_path.exists():
        raise FileNotFoundError(md_path)

    lines = md_path.read_text(encoding="utf-8").splitlines()

    fixed_lines = []
    buffer = ""

    for line in lines:
        line = line.rstrip()

        # Remove Công Báo noise
        if is_cong_bao_line(line):
            continue

        line = normalize_alpha_bullet(line)

        if is_special_line(line):
            if buffer:
                fixed_lines.append(buffer)
                buffer = ""
            fixed_lines.append(line)
            continue

        if buffer:
            if not buffer.endswith(END_SENTENCE_CHARS):
                buffer += " " + line.strip()
            else:
                fixed_lines.append(buffer)
                buffer = line
        else:
            buffer = line

    if buffer:
        fixed_lines.append(buffer)

    return "\n".join(fixed_lines)


def main():
    if not MD_RAW_DIR.exists():
        raise RuntimeError(f"Markdown input dir not found: {MD_RAW_DIR}")

    MD_FIXED_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(MD_RAW_DIR.glob("*.md"))
    if not md_files:
        raise RuntimeError(f"No markdown files found in {MD_RAW_DIR}")

    for md_path in md_files:
        out_path = MD_FIXED_DIR / f"{md_path.stem}-{FIX_VERSION}.md"

        fixed_content = fix_broken_lines(md_path)
        out_path.write_text(fixed_content, encoding="utf-8")

        print(f"[OK] {md_path.name} → {out_path.name}")


if __name__ == "__main__":
    main()
