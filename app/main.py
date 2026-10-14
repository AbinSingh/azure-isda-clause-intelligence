from fastapi import FastAPI

app = FastAPI(
    title="ISDA Clause Intelligence",
    version="0.1.0",
    description="Clause-aware ingestion and retrieval for ISDA agreements.",
)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "isda-clause-intelligence"}
