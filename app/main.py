import json
import logging

from pathlib import Path

from app.services.document_intelligence import (
    DocumentIntelligenceService,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    # Example PDF path.
    # Replace this with the path to your actual PDF.
    pdf_path = Path("isda_agreement.pdf")

    service = DocumentIntelligenceService()

    result = service.analyze_pdf(pdf_path)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
