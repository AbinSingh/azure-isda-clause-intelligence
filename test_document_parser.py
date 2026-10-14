from pathlib import Path
from app.services.document_parser import DocumentParser


PROJECT_ROOT = Path(__file__).resolve().parent

# Replace this with the path to one actual cached JSON file.
json_path = (
    PROJECT_ROOT
    / "app"
    / "data"
    / "524aa7ec-8286-46ec-8c28-b4c1d42c53e6.json"
)

parser = DocumentParser()

parsed_document = parser.parse_file(json_path)

print("Document metadata:")
print(parsed_document["document_metadata"])

print("\nTotal paragraphs:", len(parsed_document["paragraphs"]))
print("Total pages:", len(parsed_document["pages"]))
print("Total tables:", len(parsed_document["tables"]))
print("Total sections:", len(parsed_document["sections"]))

print("\nFirst 20 paragraphs:")

for paragraph in parsed_document["paragraphs"][:20]:
    print(
        f'Paragraph {paragraph["paragraph_index"]} | '
        f'Pages {paragraph["page_numbers"]} | '
        f'Role {paragraph["role"]} | '
        f'Text: {paragraph["text"][:200]}'
    )

for paragraph in parsed_document["paragraphs"][20:]:
    print(
        f'Paragraph {paragraph["paragraph_index"]} | '
        f'Pages {paragraph["page_numbers"]} | '
        f'Role {paragraph["role"]} | '
        f'Text: {paragraph["text"]}'
    )