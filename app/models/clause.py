from dataclasses import dataclass, field
from typing import Any


@dataclass
class Clause:
    """
    Represents a section, clause, or subclause extracted
    from an ISDA 2002 Master Agreement.
    """

    clause_id: str
    clause_number: str
    clause_title: str

    # Hierarchical relationship
    parent_clause_id: str | None = None
    level: int = 0

    # Actual text extracted from the agreement
    text: str = ""

    # Source information
    document_id: str | None = None
    source_filename: str | None = None
    page_start: int | None = None
    page_end: int | None = None

    # IDs of child clauses
    child_clause_ids: list[str] = field(default_factory=list)

    # Additional extraction information
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the clause into a dictionary suitable
        for JSON serialization.
        """
        return {
            "clause_id": self.clause_id,
            "clause_number": self.clause_number,
            "clause_title": self.clause_title,
            "parent_clause_id": self.parent_clause_id,
            "level": self.level,
            "text": self.text,
            "document_id": self.document_id,
            "source_filename": self.source_filename,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "child_clause_ids": self.child_clause_ids,
            "metadata": self.metadata,
        }

