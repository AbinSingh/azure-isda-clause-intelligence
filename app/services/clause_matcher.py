import re
from typing import Any

from app.models.clause import Clause
from app.services.clause_registry import ClauseRegistry


class ClauseMatcher:
    """
    Identifies clause boundaries in a normalized ISDA 2002
    Master Agreement.

    This is a structure-aware baseline matcher. It uses numbering,
    parent context, and the optional clause registry to assemble
    clauses from Azure-normalized paragraphs.
    """

    SECTION_PATTERN = re.compile(
        r"^\s*(\d{1,2})\.\s+(.+?)\s*$"
    )

    LETTER_PATTERN = re.compile(
        r"^\s*\(([a-z])\)\s*(.*)$",
        re.IGNORECASE,
    )

    ROMAN_PATTERN = re.compile(
        r"^\s*\((i{1,3}|iv|v|vi{0,3}|ix|x)\)"
        r"(?:\s+|$)(.*)$",
        re.IGNORECASE,
    )

    NUMBERED_ITEM_PATTERN = re.compile(
        r"^\s*\((\d{1,2})\)\s*(.*)$"
    )

    FOOTER_ROLES = {
        "pageFooter",
        "pageNumber",
    }

    def __init__(
        self,
        registry: ClauseRegistry | None = None,
    ):
        self.registry = registry

    def match(
        self,
        parsed_document: dict[str, Any],
    ) -> list[Clause]:
        paragraphs = parsed_document.get("paragraphs", [])

        if not isinstance(paragraphs, list):
            raise ValueError(
                "parsed_document['paragraphs'] must be a list."
            )

        document_metadata = parsed_document.get(
            "document_metadata",
            {},
        )

        document_id = document_metadata.get("id")
        source_filename = document_metadata.get(
            "source_filename"
        )

        clauses: list[Clause] = []

        current_section: Clause | None = None
        current_subsection: Clause | None = None
        current_provision: Clause | None = None
        current_numbered_item: Clause | None = None

        for paragraph in paragraphs:
            if not isinstance(paragraph, dict):
                continue

            text = self._clean_text(
                paragraph.get("text", "")
            )

            if not text:
                continue

            role = paragraph.get("role")

            if role in self.FOOTER_ROLES:
                continue

            page_start, page_end = self._get_page_range(
                paragraph.get("page_numbers", [])
            )

            paragraph_index = paragraph.get(
                "paragraph_index"
            )

            # --------------------------------------------------
            # 1. Main section, e.g. "2. Obligations"
            # --------------------------------------------------
            section_match = self.SECTION_PATTERN.match(text)

            if section_match:
                number = section_match.group(1)
                title = self._clean_title(
                    section_match.group(2)
                )

                current_section = self._create_clause(
                    number=number,
                    title=title,
                    level=0,
                    parent=None,
                    text=text,
                    document_id=document_id,
                    source_filename=source_filename,
                    page_start=page_start,
                    page_end=page_end,
                    paragraph_index=paragraph_index,
                )

                clauses.append(current_section)

                current_subsection = None
                current_provision = None
                current_numbered_item = None

                continue

            if current_section is None:
                # Ignore document front matter.
                continue

            # --------------------------------------------------
            # 2. Roman-numbered provision.
            #
            # Must come BEFORE the lettered-subsection check.
            # For example, "(i)" must not be interpreted as "(i)"
            # being a lettered subsection.
            # --------------------------------------------------
            roman_match = self.ROMAN_PATTERN.match(text)

            if (
                roman_match
                and current_subsection is not None
            ):
                roman = roman_match.group(1).lower()
                remainder = roman_match.group(2).strip()

                title = ""

                # Some numbered provisions include a named
                # heading, e.g. "(i) Gross-Up. All payments..."
                if remainder:
                    possible_title, possible_body = (
                        self._split_title_and_body(remainder)
                    )

                    registry_entry = None

                    if self.registry is not None:
                        candidate_number = (
                            f"{current_subsection.clause_number}"
                            f"({roman})"
                        )

                        registry_entry = (
                            self.registry.get_by_number(
                                candidate_number
                            )
                        )

                    registry_title = (
                        registry_entry.get("clause_title", "")
                        if registry_entry
                        else ""
                    )

                    if (
                            registry_title
                            and possible_title.casefold()
                            == registry_title.casefold()
                    ):
                        title = possible_title
                        body = possible_body
                    else:
                        body = remainder

                provision_number = (
                    f"{current_subsection.clause_number}"
                    f"({roman})"
                )

                current_provision = self._create_clause(
                    number=provision_number,
                    title="",
                    level=2,
                    parent=current_subsection,
                    text=body,
                    document_id=document_id,
                    source_filename=source_filename,
                    page_start=page_start,
                    page_end=page_end,
                    paragraph_index=paragraph_index,
                )

                clauses.append(current_provision)

                current_numbered_item = None

                continue

            # --------------------------------------------------
            # 3. Nested numbered item, e.g. "(1) promptly notify"
            # --------------------------------------------------
            numbered_match = self.NUMBERED_ITEM_PATTERN.match(
                text
            )

            if (
                numbered_match
                and current_provision is not None
            ):
                item_number = numbered_match.group(1)
                body = numbered_match.group(2).strip()

                nested_number = (
                    f"{current_provision.clause_number}"
                    f"({item_number})"
                )

                current_numbered_item = self._create_clause(
                    number=nested_number,
                    title="",
                    level=3,
                    parent=current_provision,
                    text=body,
                    document_id=document_id,
                    source_filename=source_filename,
                    page_start=page_start,
                    page_end=page_end,
                    paragraph_index=paragraph_index,
                )

                clauses.append(current_numbered_item)

                continue

            # --------------------------------------------------
            # 4. Lettered subsection, e.g. "(a) General Conditions."
            # --------------------------------------------------
            letter_match = self.LETTER_PATTERN.match(text)

            if letter_match:
                letter = letter_match.group(1).lower()
                remainder = letter_match.group(2).strip()

                title, body = self._split_title_and_body(
                    remainder
                )

                subsection_number = (
                    f"{current_section.clause_number}"
                    f"({letter})"
                )

                current_subsection = self._create_clause(
                    number=subsection_number,
                    title=title,
                    level=1,
                    parent=current_section,
                    text=body,
                    document_id=document_id,
                    source_filename=source_filename,
                    page_start=page_start,
                    page_end=page_end,
                    paragraph_index=paragraph_index,
                )

                clauses.append(current_subsection)

                current_provision = None
                current_numbered_item = None

                continue

            # --------------------------------------------------
            # 5. Continuation paragraph.
            #
            # Append it to the most specific active clause.
            # --------------------------------------------------
            target = (
                current_numbered_item
                or current_provision
                or current_subsection
                or current_section
            )

            self._append_text(
                target,
                text,
                page_start,
                page_end,
                paragraph_index,
            )

        return clauses

    def _create_clause(
        self,
        number: str,
        title: str,
        level: int,
        parent: Clause | None,
        text: str,
        document_id: str | None,
        source_filename: str | None,
        page_start: int | None,
        page_end: int | None,
        paragraph_index: int | None,
    ) -> Clause:
        registry_entry = None

        if self.registry is not None:
            registry_entry = self.registry.get_by_number(
                number
            )

        if registry_entry:
            clause_id = registry_entry["clause_id"]
        else:
            safe_number = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                number,
            ).strip("_")

            clause_id = f"section_{safe_number}"

        if (
            registry_entry
            and not title
            and registry_entry.get("clause_title")
        ):
            title = registry_entry["clause_title"]

        clause = Clause(
            clause_id=clause_id,
            clause_number=number,
            clause_title=title,
            parent_clause_id=(
                parent.clause_id if parent else None
            ),
            level=level,
            text=text,
            document_id=document_id,
            source_filename=source_filename,
            page_start=page_start,
            page_end=page_end,
            child_clause_ids=[],
            metadata={
                "paragraph_indices": (
                    [paragraph_index]
                    if paragraph_index is not None
                    else []
                ),
                "registry_matched": (
                    registry_entry is not None
                ),
            },
        )

        if parent is not None:
            parent.child_clause_ids.append(
                clause.clause_id
            )

        return clause

    @staticmethod
    def _append_text(
        clause: Clause,
        text: str,
        page_start: int | None,
        page_end: int | None,
        paragraph_index: int | None,
    ) -> None:
        if not text:
            return

        if clause.text:
            clause.text = f"{clause.text} {text}"
        else:
            clause.text = text

        if page_start is not None:
            if clause.page_start is None:
                clause.page_start = page_start
            else:
                clause.page_start = min(
                    clause.page_start,
                    page_start,
                )

        if page_end is not None:
            if clause.page_end is None:
                clause.page_end = page_end
            else:
                clause.page_end = max(
                    clause.page_end,
                    page_end,
                )

        if paragraph_index is not None:
            indices = clause.metadata.setdefault(
                "paragraph_indices",
                [],
            )

            if paragraph_index not in indices:
                indices.append(paragraph_index)

    @staticmethod
    def _get_page_range(
        page_numbers: Any,
    ) -> tuple[int | None, int | None]:
        if not isinstance(page_numbers, list):
            return None, None

        valid_pages = [
            page
            for page in page_numbers
            if isinstance(page, int)
        ]

        if not valid_pages:
            return None, None

        return min(valid_pages), max(valid_pages)

    @staticmethod
    def _clean_text(text: Any) -> str:
        if not isinstance(text, str):
            return ""

        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _clean_title(title: str) -> str:
        return title.strip().rstrip(" .:-")

    @staticmethod
    def _split_title_and_body(
        remainder: str,
    ) -> tuple[str, str]:
        """
        Split a subsection heading from its body.

        Examples:
            "General Conditions." ->
                ("General Conditions", "")

            "Definitions. The terms defined..." ->
                ("Definitions", "The terms defined...")

            "Gross-Up. All payments..." ->
                ("Gross-Up", "All payments...")
        """

        remainder = remainder.strip()

        if not remainder:
            return "", ""

        match = re.match(
            r"^(.+?)\.\s+(.+)$",
            remainder,
        )

        if match:
            title = match.group(1).strip()
            body = match.group(2).strip()

            return title, body

        return remainder.rstrip(" .:-"), ""