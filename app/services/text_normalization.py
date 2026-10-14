"""Conservative normalization for extracted PDF text.

The original extracted string should be retained separately. This module creates a
working representation for structural detection; it must not be used to rewrite
contractual source text shown as evidence.
"""

import re


def normalize_extracted_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    # Normalize line endings and common non-breaking spaces.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u202f", " ")

    # Remove Markdown emphasis delimiters while retaining the words inside them.
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"\1", text)

    # Convert a two-cell Markdown table row like "| 2. | Obligations |"
    # into a heading candidate. This intentionally handles only simple rows.
    converted_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            cells = [re.sub(r"[*_]", "", cell).strip() for cell in cells]
            nonempty = [cell for cell in cells if cell]
            if (
                len(nonempty) >= 2
                and re.fullmatch(r"\d{1,2}\.", nonempty[0])
                and not all(re.fullmatch(r"[:\- ]+", c or "-") for c in cells)
            ):
                converted_lines.append(f"{nonempty[0]} {nonempty[1]}")
            else:
                # Drop pure Markdown separator rows and empty layout tables.
                if all(re.fullmatch(r"[:\-\s]*", c) for c in cells):
                    continue
                if not any(c for c in cells):
                    continue
                converted_lines.append(line)
        else:
            converted_lines.append(line)

    text = "\n".join(converted_lines)

    # Remove horizontal page separators, but do not remove arbitrary content.
    text = re.sub(r"(?m)^\s*---+\s*$", "", text)

    # Collapse excessive blank lines; preserve single blank lines as paragraph boundaries.
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text)
    return text.strip()
