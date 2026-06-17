"""Markdown to Feishu Docx Block format converter."""

from __future__ import annotations

import re
from typing import Any


def markdown_to_feishu_blocks(md: str) -> list[dict[str, Any]]:
    """Convert a markdown string into Feishu docx blocks."""
    lines = md.split("\n")
    blocks: list[dict[str, Any]] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("### "):
            blocks.append(_heading(5, stripped[4:]))
        elif stripped.startswith("## "):
            blocks.append(_heading(4, stripped[3:]))
        elif stripped.startswith("# "):
            blocks.append(_heading(3, stripped[2:]))
        elif re.match(r"^-{3,}$", stripped):
            blocks.append({"block_type": 22, "divider": {}})
        elif re.match(r"^[-*] ", stripped):
            blocks.append(_block(12, "bullet", re.sub(r"^[-*] ", "", stripped)))
        elif re.match(r"^\d+\. ", stripped):
            blocks.append(_block(13, "ordered", re.sub(r"^\d+\. ", "", stripped)))
        elif stripped.startswith("> "):
            blocks.append(_block(15, "quote", stripped[2:]))
        elif stripped.startswith("|"):
            table_lines = [stripped]
            index += 1
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            blocks.append(_table(table_lines))
            continue
        else:
            blocks.append(_block(2, "text", stripped))

        index += 1

    return blocks


def _heading(level: int, text: str) -> dict[str, Any]:
    key = f"heading{level - 2}"
    return {
        "block_type": level,
        key: {"elements": _text_elements(text), "style": {}},
    }


def _block(block_type: int, key: str, text: str) -> dict[str, Any]:
    return {
        "block_type": block_type,
        key: {"elements": _text_elements(text), "style": {}},
    }


def _run(content: str, style: dict[str, Any]) -> dict[str, Any]:
    return {"text_run": {"content": content, "text_element_style": style}}


def _text_elements(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"\*\*(?P<bold>.+?)\*\*"
        r"|\*(?P<italic>.+?)\*"
        r"|`(?P<code>.+?)`"
        r"|\[(?P<link_text>.+?)\]\((?P<link_url>.+?)\)"
        r"|(?P<plain>[^*`\[]+)"
        r"|(?P<fallback>.)"
    )
    elements: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        if match.group("bold"):
            elements.append(_run(match.group("bold"), {"bold": True}))
        elif match.group("italic"):
            elements.append(_run(match.group("italic"), {"italic": True}))
        elif match.group("code"):
            elements.append(_run(match.group("code"), {"inline_code": True}))
        elif match.group("link_text"):
            elements.append(_run(match.group("link_text"), {"link": {"url": match.group("link_url")}}))
        elif match.group("plain"):
            elements.append(_run(match.group("plain"), {}))
        elif match.group("fallback"):
            elements.append(_run(match.group("fallback"), {}))
    return elements or [_run(text, {})]


def _table(lines: list[str]) -> dict[str, Any]:
    parsed_rows: list[list[str]] = []
    for line in lines:
        if _is_table_separator(line):
            continue
        cells = _parse_table_row(line)
        if cells:
            parsed_rows.append(cells)

    if not parsed_rows:
        return _block(2, "text", " | ".join(lines))

    num_rows = len(parsed_rows)
    num_cols = max(len(row) for row in parsed_rows)
    table_rows = []
    for row in parsed_rows:
        table_row = []
        for col_idx in range(num_cols):
            cell_text = row[col_idx].strip() if col_idx < len(row) else ""
            table_row.append({
                "text": cell_text or " ",
                "elements": _text_elements(cell_text or " "),
            })
        table_rows.append(table_row)

    return {
        "block_type": 31,
        "table": {"property": {"row_size": num_rows, "column_size": num_cols}},
        "_table_rows": table_rows,
    }


def _is_table_separator(line: str) -> bool:
    stripped = line.strip().lstrip("|").rstrip("|")
    parts = [part.strip() for part in stripped.split("|")]
    return all(all(char in "-: " for char in part) and len(part) > 0 for part in parts)


def _parse_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]
