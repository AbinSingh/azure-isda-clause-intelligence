import json
from pathlib import Path
from typing import Any


class ClauseRegistry:
    """
    Loads the canonical clause registry and provides
    lookup by clause ID and clause number.
    """

    def __init__(self, registry_path: str | Path):
        self.registry_path = Path(registry_path)

        self.registry: dict[str, Any] = {}
        self.clauses_by_id: dict[str, dict[str, Any]] = {}
        self.clauses_by_number: dict[str, dict[str, Any]] = {}

        self.load()

    def load(self) -> None:
        """Load the registry and build lookup indexes."""

        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"Clause registry not found: {self.registry_path}"
            )

        with self.registry_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            self.registry = json.load(file)

        self.clauses_by_id.clear()
        self.clauses_by_number.clear()

        for section in self.registry.get("sections", []):
            self._index_clause(section)

    def _index_clause(self, clause: dict[str, Any]) -> None:
        """Index a clause and recursively index its children."""

        clause_id = clause["clause_id"]
        clause_number = clause["clause_number"]

        if clause_id in self.clauses_by_id:
            raise ValueError(
                f"Duplicate clause ID in registry: {clause_id}"
            )

        if clause_number in self.clauses_by_number:
            raise ValueError(
                f"Duplicate clause number in registry: {clause_number}"
            )

        self.clauses_by_id[clause_id] = clause
        self.clauses_by_number[clause_number] = clause

        for child in clause.get("children", []):
            self._index_clause(child)

    def get_by_id(
        self,
        clause_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a clause by its internal ID."""

        return self.clauses_by_id.get(clause_id)

    def get_by_number(
        self,
        clause_number: str,
    ) -> dict[str, Any] | None:
        """Retrieve a clause by its clause number."""

        return self.clauses_by_number.get(clause_number)

    def get_all_clauses(self) -> list[dict[str, Any]]:
        """Return all registered clauses in traversal order."""

        return list(self.clauses_by_id.values())