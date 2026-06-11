from __future__ import annotations

from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


INPUT = PROJECT_ROOT / "docs" / "project" / "professor_review_brief.md"
OUTPUT = PROJECT_ROOT / "docs" / "project" / "professor_review_brief.pdf"
FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/Library/Fonts/NotoSansCJKkr-Regular.otf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
]


def strip_inline_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text


def parse_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    lines = markdown.splitlines()
    index = 0
    in_code = False
    code_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                blocks.append({"type": "code", "lines": code_lines})
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if stripped == "<!-- pagebreak -->":
            blocks.append({"type": "pagebreak"})
            index += 1
            continue
        if not stripped or stripped == "<!-- spacer -->":
            index += 1
            continue
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = []
            for table_line in table_lines:
                cells = [strip_inline_markdown(cell.strip()) for cell in table_line.strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
                    continue
                rows.append(cells)
            if rows:
                blocks.append({"type": "table", "rows": rows})
            continue
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            blocks.append({"type": "heading", "level": level, "text": strip_inline_markdown(text)})
            index += 1
            continue
        if stripped.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(strip_inline_markdown(lines[index].strip()[2:].strip()))
                index += 1
            blocks.append({"type": "list", "items": items})
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                items.append(strip_inline_markdown(re.sub(r"^\d+\.\s+", "", lines[index].strip())))
                index += 1
            blocks.append({"type": "numbered", "items": items})
            continue
        if stripped.startswith(">"):
            blocks.append({"type": "quote", "text": strip_inline_markdown(stripped.lstrip(">").strip())})
            index += 1
            continue
        paragraph = [stripped]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if (
                not next_line
                or next_line.startswith("#")
                or next_line.startswith("|")
                or next_line.startswith("- ")
                or next_line.startswith("```")
                or next_line == "<!-- pagebreak -->"
                or re.match(r"^\d+\.\s+", next_line)
            ):
                break
            paragraph.append(next_line)
            index += 1
        blocks.append({"type": "paragraph", "text": strip_inline_markdown(" ".join(paragraph))})
    return blocks


def build_pdf() -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        KeepTogether,
        ListFlowable,
        ListItem,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        XPreformatted,
    )

    font_name = "Helvetica"
    for font_path in FONT_CANDIDATES:
        if not font_path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("KoreanBody", str(font_path)))
            font_name = "KoreanBody"
            break
        except Exception:
            continue

    page_width, page_height = A4
    body_width = 148 * mm
    left_margin = (page_width - body_width) / 2
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "BaseKorean",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.2,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    h1 = ParagraphStyle("H1", parent=base, fontSize=16, leading=22, spaceBefore=4, spaceAfter=12, alignment=TA_CENTER)
    h2 = ParagraphStyle("H2", parent=base, fontSize=13, leading=18, spaceBefore=14, spaceAfter=8)
    h3 = ParagraphStyle("H3", parent=base, fontSize=11, leading=16, spaceBefore=10, spaceAfter=6)
    quote = ParagraphStyle(
        "Quote",
        parent=base,
        leftIndent=10,
        rightIndent=10,
        borderColor=colors.HexColor("#D0D7DE"),
        borderWidth=0.5,
        borderPadding=6,
        backColor=colors.HexColor("#F6F8FA"),
    )
    code = ParagraphStyle(
        "Code",
        parent=base,
        fontName=font_name,
        fontSize=8.3,
        leading=12,
        backColor=colors.HexColor("#F6F8FA"),
        borderColor=colors.HexColor("#D0D7DE"),
        borderWidth=0.4,
        borderPadding=5,
    )

    story = []
    for block in parse_blocks(INPUT.read_text(encoding="utf-8")):
        block_type = block["type"]
        if block_type == "pagebreak":
            story.append(PageBreak())
        elif block_type == "heading":
            level = block["level"]
            style = h1 if level == 1 else h2 if level == 2 else h3
            story.append(Paragraph(block["text"], style))
        elif block_type == "paragraph":
            story.append(Paragraph(block["text"], base))
        elif block_type == "quote":
            story.append(Paragraph(block["text"], quote))
        elif block_type == "list":
            items = [ListItem(Paragraph(item, base), leftIndent=8) for item in block["items"]]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=14, bulletFontName=font_name, bulletFontSize=7))
            story.append(Spacer(1, 2))
        elif block_type == "numbered":
            items = [ListItem(Paragraph(item, base), leftIndent=8) for item in block["items"]]
            story.append(ListFlowable(items, bulletType="1", leftIndent=16, bulletFontName=font_name, bulletFontSize=8))
            story.append(Spacer(1, 2))
        elif block_type == "code":
            story.append(XPreformatted("\n".join(block["lines"]), code))
            story.append(Spacer(1, 4))
        elif block_type == "table":
            rows = block["rows"]
            col_count = max(len(row) for row in rows)
            normalized_rows = [row + [""] * (col_count - len(row)) for row in rows]
            table_data = [[Paragraph(cell, base) for cell in row] for row in normalized_rows]
            col_width = body_width / col_count
            table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.3),
                        ("LEADING", (0, 0), (-1, -1), 11),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(KeepTogether([table, Spacer(1, 7)]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawCentredString(page_width / 2, 10 * mm, f"무장애·가족 친화 관광 챗봇 시제품 검토 자료    {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=left_margin,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="무장애 가족 친화 관광 챗봇 시제품 검토 자료",
        author="chatbot_rag",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build_pdf()
    print({"output": str(OUTPUT.relative_to(PROJECT_ROOT))})
