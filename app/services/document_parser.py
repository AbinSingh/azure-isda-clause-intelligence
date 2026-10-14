import json
from pathlib import Path
from typing import Any


class DocumentParser:
    """
    Normalizes the raw JSON returned by Azure AI Document
    Intelligence into a consistent document representation.

    This class does not identify clauses or create chunks.
    Those responsibilities belong to later pipeline stages.
    """

    def parse_file(self, json_path: str | Path) -> dict[str, Any]:
        """
        Read a cached Azure JSON file and normalize its contents.
        """

        path = Path(json_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Azure JSON file not found: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        if not isinstance(raw_data, dict):
            raise ValueError(
                "The Azure JSON root must be a JSON object."
            )

        return self.parse_dict(raw_data)

    def parse_dict(
        self,
        raw_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a dictionary containing an Azure analysis result.
        """

        # Support either a raw AnalyzeResult dictionary or the
        # cache envelope used by the existing application.
        analyze_result = raw_data.get("analyze_result", raw_data)

        if not isinstance(analyze_result, dict):
            raise ValueError(
                "Expected an Azure AnalyzeResult JSON object."
            )

        content = analyze_result.get("content", "")

        if not isinstance(content, str):
            content = ""

        paragraphs = analyze_result.get("paragraphs", [])
        pages = analyze_result.get("pages", [])
        tables = analyze_result.get("tables", [])
        sections = analyze_result.get("sections", [])

        if not isinstance(paragraphs, list):
            paragraphs = []

        if not isinstance(pages, list):
            pages = []

        if not isinstance(tables, list):
            tables = []

        if not isinstance(sections, list):
            sections = []

        normalized_paragraphs = [
            self._normalize_paragraph(index, paragraph)
            for index, paragraph in enumerate(paragraphs)
            if isinstance(paragraph, dict)
        ]

        normalized_pages = [
            self._normalize_page(index, page)
            for index, page in enumerate(pages)
            if isinstance(page, dict)
        ]

        normalized_tables = [
            self._normalize_table(index, table)
            for index, table in enumerate(tables)
            if isinstance(table, dict)
        ]

        normalized_sections = [
            self._normalize_section(index, section)
            for index, section in enumerate(sections)
            if isinstance(section, dict)
        ]

        # Cache metadata may be present if the existing service
        # stores the analysis result inside an envelope.
        cache_metadata = {
            key: raw_data.get(key)
            for key in (
                "id",
                "pdf_sha256",
                "source_filename",
                "model_id",
            )
            if key in raw_data
        }

        return {
            "document_metadata": {
                "api_version": analyze_result.get("apiVersion"),
                "model_id": analyze_result.get("modelId"),
                "string_index_type": analyze_result.get(
                    "stringIndexType"
                ),
                "content_format": analyze_result.get(
                    "contentFormat"
                ),
                **cache_metadata,
            },
            "content": content,
            "paragraphs": normalized_paragraphs,
            "pages": normalized_pages,
            "tables": normalized_tables,
            "sections": normalized_sections,
            "styles": analyze_result.get("styles", []),
        }

    def _normalize_paragraph(
        self,
        index: int,
        paragraph: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a single paragraph and retain source metadata.
        """

        bounding_regions = paragraph.get("boundingRegions", [])

        if not isinstance(bounding_regions, list):
            bounding_regions = []

        normalized_regions = []

        for region in bounding_regions:
            if not isinstance(region, dict):
                continue

            normalized_regions.append(
                {
                    "page_number": region.get("pageNumber"),
                    "polygon": region.get("polygon", []),
                }
            )

        page_numbers = sorted(
            {
                region["page_number"]
                for region in normalized_regions
                if isinstance(region["page_number"], int)
            }
        )

        spans = paragraph.get("spans", [])

        if not isinstance(spans, list):
            spans = []

        return {
            "paragraph_index": index,
            "text": paragraph.get("content", ""),
            "role": paragraph.get("role"),
            "spans": spans,
            "page_numbers": page_numbers,
            "bounding_regions": normalized_regions,
        }

    def _normalize_page(
        self,
        index: int,
        page: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize page-level metadata.
        """

        return {
            "page_index": index,
            "page_number": page.get("pageNumber"),
            "width": page.get("width"),
            "height": page.get("height"),
            "unit": page.get("unit"),
            "angle": page.get("angle"),
            "spans": page.get("spans", []),
            "words": page.get("words", []),
            "lines": page.get("lines", []),
        }

    def _normalize_table(
        self,
        index: int,
        table: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize table metadata while retaining cell contents
        and their relationships.
        """

        bounding_regions = table.get("boundingRegions", [])

        if not isinstance(bounding_regions, list):
            bounding_regions = []

        normalized_regions = [
            {
                "page_number": region.get("pageNumber"),
                "polygon": region.get("polygon", []),
            }
            for region in bounding_regions
            if isinstance(region, dict)
        ]

        cells = table.get("cells", [])

        if not isinstance(cells, list):
            cells = []

        normalized_cells = []

        for cell in cells:
            if not isinstance(cell, dict):
                continue

            normalized_cells.append(
                {
                    "row_index": cell.get("rowIndex"),
                    "column_index": cell.get("columnIndex"),
                    "row_span": cell.get("rowSpan", 1),
                    "column_span": cell.get("columnSpan", 1),
                    "content": cell.get("content", ""),
                    "kind": cell.get("kind"),
                    "spans": cell.get("spans", []),
                    "elements": cell.get("elements", []),
                }
            )

        return {
            "table_index": index,
            "row_count": table.get("rowCount"),
            "column_count": table.get("columnCount"),
            "bounding_regions": normalized_regions,
            "cells": normalized_cells,
            "spans": table.get("spans", []),
        }

    def _normalize_section(
        self,
        index: int,
        section: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize Azure section references.

        Section elements are preserved because they may reference
        paragraphs or other sections in the Azure result.
        """

        return {
            "section_index": index,
            "spans": section.get("spans", []),
            "elements": section.get("elements", []),
        }
