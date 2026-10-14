from pydantic import BaseModel, Field


class StructuralNode(BaseModel):
    """A detected structural element. Text remains source-derived, not paraphrased."""

    node_id: str
    node_type: str
    identifier: str | None = None
    title: str | None = None
    text: str = ""
    parent_node_id: str | None = None
    children: list["StructuralNode"] = Field(default_factory=list)
    detection_method: str = "rule_based"
    confidence: float = 0.0


class ParsedDocument(BaseModel):
    document_id: str
    parser_version: str = "0.1.0"
    sections: list[StructuralNode] = Field(default_factory=list)
    unassigned_paragraphs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
