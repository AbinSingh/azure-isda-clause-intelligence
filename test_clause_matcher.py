from pathlib import Path

from app.services.document_parser import DocumentParser
from app.services.clause_registry import ClauseRegistry
from app.services.clause_matcher import ClauseMatcher


PROJECT_ROOT = Path(__file__).resolve().parent

JSON_PATH = PROJECT_ROOT / "app" / "data" / "524aa7ec-8286-46ec-8c28-b4c1d42c53e6.json"

REGISTRY_PATH = (
    PROJECT_ROOT
    / "app"
    / "schemas"
    / "isda_clause_registry.json"
)


def main():
    parser = DocumentParser()

    registry = ClauseRegistry(REGISTRY_PATH)

    matcher = ClauseMatcher(registry)

    parsed_document = parser.parse_file(JSON_PATH)

    clauses = matcher.match(parsed_document)

    print(f"\nTotal clauses detected: {len(clauses)}\n")

    for clause in clauses:
        print("-" * 80)

        print(f"Number: {clause.clause_number}")
        print(f"Title: {clause.clause_title}")
        print(f"Level: {clause.level}")
        print(f"Parent: {clause.parent_clause_id}")
        print(f"Pages: {clause.page_start}-{clause.page_end}")
        print(f"Text: {clause.text[:250]}")
        print(
            f"Children: {clause.child_clause_ids}"
        )

    print("\n\nFOCUSED CLAUSE VALIDATION")
    print("=" * 80)

    target_numbers = {
        "2(a)(iii)",
        "2(c)",
        "2(c)(ii)",
        "2(d)(i)",
        "2(d)(i)(1)",
        "2(d)(i)(2)",
        "2(d)(i)(3)",
    }

    for clause in clauses:
        if clause.clause_number not in target_numbers:
            continue

        print("\n" + "-" * 80)
        print(f"Clause: {clause.clause_number}")
        print(f"Title: {clause.clause_title}")
        print(f"Pages: {clause.page_start}-{clause.page_end}")
        print(
            "Paragraph indices:",
            clause.metadata.get("paragraph_indices", []),
        )
        print(f"Text length: {len(clause.text)}")
        print("Full text:")
        print(clause.text)


if __name__ == "__main__":
    main()