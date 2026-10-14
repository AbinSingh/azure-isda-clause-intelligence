import hashlib
import json
import logging
import uuid

from pathlib import Path
from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.core.serialization import AzureJSONEncoder

from app.config import (
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
    AZURE_DOCUMENT_INTELLIGENCE_KEY,
    AZURE_DOCUMENT_INTELLIGENCE_MODEL,
    DATA_DIR,
    validate_config,
)


logger = logging.getLogger(__name__)


class DocumentIntelligenceService:
    """
    Analyze PDFs using Azure Document Intelligence.

    Results are cached in app/data using:
      - SHA-256 for identifying identical PDF content
      - UUID for naming output JSON files
    """

    def __init__(self):
        validate_config()

        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.client = DocumentIntelligenceClient(
            endpoint=AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(
                AZURE_DOCUMENT_INTELLIGENCE_KEY
            ),
        )

        self.model_id = AZURE_DOCUMENT_INTELLIGENCE_MODEL

    @staticmethod
    def _calculate_sha256(pdf_path: Path) -> str:
        """Calculate the SHA-256 hash of a PDF."""

        sha256 = hashlib.sha256()

        with pdf_path.open("rb") as pdf_file:
            for chunk in iter(
                lambda: pdf_file.read(1024 * 1024),
                b"",
            ):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _find_cached_result(
        self,
        pdf_sha256: str,
    ) -> dict[str, Any] | None:
        """
        Find an existing JSON result for the same PDF contents.
        """

        for json_path in self.data_dir.glob("*.json"):
            try:
                with json_path.open(
                    "r",
                    encoding="utf-8",
                ) as json_file:
                    cached_result = json.load(json_file)

                metadata = cached_result.get("_cache_metadata", {})

                if metadata.get("pdf_sha256") == pdf_sha256:
                    logger.info(
                        "Using cached Document Intelligence result: %s",
                        json_path.name,
                    )
                    return cached_result

            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping unreadable cache file %s: %s",
                    json_path.name,
                    exc,
                )

        return None

    def analyze_pdf(
        self,
        pdf_file_path: str | Path,
    ) -> dict[str, Any]:
        """
        Analyze a PDF or return its cached analysis.

        Returns:
            A dictionary containing cache metadata and the complete
            Azure Document Intelligence analysis result.
        """
        pdf_path = Path(pdf_file_path)

        if not pdf_path.is_absolute():
            pdf_path = Path(__file__).resolve().parent.parent / pdf_path

        pdf_path = pdf_path.resolve()

        if not pdf_path.is_file():
            raise FileNotFoundError(
                f"PDF file not found: {pdf_path.resolve()}"
            )

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("The input file must have a .pdf extension.")

        # Step 1: Identify the PDF by its content.
        pdf_sha256 = self._calculate_sha256(pdf_path)

        # Step 2: Check the cache before calling Azure.
        cached_result = self._find_cached_result(pdf_sha256)

        if cached_result is not None:
            return cached_result

        logger.info(
            "No cached result found. Submitting PDF to Azure: %s",
            pdf_path.name,
        )

        # Step 3: Submit the PDF to Azure Document Intelligence.
        with pdf_path.open("rb") as pdf_file:
            poller = self.client.begin_analyze_document(
                model_id=self.model_id,
                body=pdf_file,
                content_type="application/octet-stream",
            )

            # Wait until the analysis finishes.
            result = poller.result()

        # Step 4: Serialize the complete SDK result to JSON-compatible data.
        # Convert the Azure SDK result into a dictionary
        result_dict = result.as_dict()

        # Convert the dictionary to a JSON-compatible string and back
        result_dict = json.loads(
            json.dumps(
                result_dict,
                ensure_ascii=False,
                default=str,
            )
        )

        # Step 5: Add cache metadata.
        output_id = str(uuid.uuid4())

        output_dict = {
            "_cache_metadata": {
                "id": output_id,
                "pdf_sha256": pdf_sha256,
                "source_filename": pdf_path.name,
                "model_id": self.model_id,
            },
            "analyze_result": result_dict,
        }

        # Step 6: Save the result using a UUID filename.
        output_path = self.data_dir / f"{output_id}.json"

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as json_file:
            json.dump(
                output_dict,
                json_file,
                indent=2,
                ensure_ascii=False,
            )

        logger.info(
            "Document analysis saved to %s",
            output_path,
        )

        return output_dict

