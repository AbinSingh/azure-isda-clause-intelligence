"""First-pass structural parser for extracted ISDA text.

Scope of v0.1:
- Finds section headings after normalization.
- Finds top-level lettered clause headings such as "(a) Definitions.".
- Associates subsequent paragraph text with the active top-level clause.
- Preserves unassigned introductory text and emits warnings for ambiguous structures.

Nested numbering is detected as candidates but is not yet promoted into a complete,
authoritative hierarchy. That is a deliberate follow-up increment.
"""

import re
from collections import defaultdict

from app.models.document_structure import ParsedDocument, StructuralNode
from app.services.marker_detection import detect_marker
from app.services.text_normalization import normalize_extracted_text

VERSION = "0.1.0"
CLAUSE_TITLE_RE = re.compile(r"^\s*\(([a-z])\)\s*(.*)$")


def _paragraphs(text: str) -> list[str]:
    # First pass: blank lines delimit paragraphs. Lines within a paragraph are joined
    # conservatively because PDF extraction often wraps a sentence across lines.
    raw_blocks = re.split(r"\n\s*\n", text)
    blocks: list[str] = []
    for block in raw_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        blocks.append(" ".join(lines))
    return blocks


def parse_document(text: str, document_id: str = "local-document") -> ParsedDocument:
    normalized = normalize_extracted_text(text)
    blocks = _paragraphs(normalized)

    sections: list[StructuralNode] = []
    unassigned: list[str] = []
    warnings: list[str] = []
    active_section: StructuralNode | None = None
    active_clause: StructuralNode | None = None
    section_counts: defaultdict[str, int] = defaultdict(int)
    clause_counts: defaultdict[str, int] = defaultdict(int)

    for block_index, block in enumerate(blocks):
        marker = detect_marker(block)

        if marker and marker.marker_type == "section":
            section_counts[marker.identifier] += 1
            section_id = f"section-{marker.identifier}-{section_counts[marker.identifier]}"
            active_section = StructuralNode(
                node_id=section_id,
                node_type="section",
                identifier=marker.identifier,
                title=marker.remainder,
                text=block,
                confidence=0.95,
            )
            sections.append(active_section)
            active_clause = None
            continue

        clause_match = CLAUSE_TITLE_RE.match(block)
        if active_section is not None and clause_match:
            identifier, remainder = clause_match.groups()

            # Resolve a common ambiguity using the expected top-level letter sequence.
            # For example, (i) under clause (a) is nested, while (d) after (c) is
            # a new top-level clause. This is a first-pass heuristic, not a universal
            # rule for every contractual document.
            existing_letters = [
                child.identifier[1:-1]
                for child in active_section.children
                if child.identifier and len(child.identifier) == 3
            ]
            expected_letter = chr(ord(existing_letters[-1]) + 1) if existing_letters else "a"
            if identifier != expected_letter:
                if active_clause is not None:
                    active_clause.text += "\n\n" + block
                else:
                    active_section.text += "\n\n" + block
                if identifier in {"i", "v", "x", "l", "c", "d", "m"}:
                    warnings.append(
                        f"Ambiguous marker ({identifier}) kept in current context at "
                        f"paragraph {block_index + 1}."
                    )
                continue

            clause_counts[active_section.node_id] += 1
            clause_id = f"{active_section.node_id}-clause-{identifier}"
            # Heading and operative text can share one extracted paragraph. Keep the
            # full block as source text, but derive a compact display title.
            title = remainder.split(". ", 1)[0].rstrip(". ").strip() or None

            active_clause = StructuralNode(
                node_id=clause_id,
                node_type="clause",
                identifier=f"({identifier})",
                title=title,
                text=block,
                parent_node_id=active_section.node_id,
                confidence=0.75,
            )
            active_section.children.append(active_clause)
            continue

        if active_clause is not None:
            active_clause.text += "\n\n" + block
        elif active_section is not None:
            # Section-level content not yet assigned to a top-level lettered clause.
            active_section.text += "\n\n" + block
            if marker and marker.marker_type in {
                "lower_alpha_or_roman",
                "upper_alpha_or_roman",
                "arabic",
            }:
                warnings.append(
                    f"Unresolved nested marker {marker.identifier!r} in section "
                    f"{active_section.identifier!r} at paragraph {block_index + 1}."
                )
        else:
            unassigned.append(block)

    if not sections:
        warnings.append("No section headings were detected.")
    if unassigned:
        warnings.append(
            f"{len(unassigned)} paragraph(s) appear before the first detected section "
            "or could not be assigned to a section."
        )

    return ParsedDocument(
        document_id=document_id,
        parser_version=VERSION,
        sections=sections,
        unassigned_paragraphs=unassigned,
        warnings=warnings,
    )
