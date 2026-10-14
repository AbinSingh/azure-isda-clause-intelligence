import os
from pathlib import Path

from dotenv import load_dotenv


# Project root: parent of the app directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from root/.env
load_dotenv(PROJECT_ROOT / ".env")

# Azure Document Intelligence settings
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv(
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
)

AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv(
    "AZURE_DOCUMENT_INTELLIGENCE_KEY"
)

AZURE_DOCUMENT_INTELLIGENCE_MODEL = os.getenv(
    "AZURE_DOCUMENT_INTELLIGENCE_MODEL",
    "prebuilt-layout",
)

# Application directories
APP_DIR = PROJECT_ROOT / "app"
DATA_DIR = APP_DIR / "data"

# Ensure the data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


def validate_config():
    """Validate required Azure configuration."""

    if not AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT:
        raise ValueError(
            "Missing AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT in .env"
        )

    if not AZURE_DOCUMENT_INTELLIGENCE_KEY:
        raise ValueError(
            "Missing AZURE_DOCUMENT_INTELLIGENCE_KEY in .env"
        )
