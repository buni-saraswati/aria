import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Cosmos DB
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    COSMOS_KEY = os.getenv("COSMOS_KEY")
    COSMOS_DATABASE = os.getenv("COSMOS_DATABASE", "aria-db")

    # Event Hub
    EVENTHUB_CONNECTION_STRING = os.getenv("EVENTHUB_CONNECTION_STRING")
    EVENTHUB_DECISIONS = os.getenv("EVENTHUB_DECISIONS", "evh-decisions")

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-41-mini-chat")

    # Blob Storage
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    SNAPSHOT_CONTAINER = os.getenv("SNAPSHOT_CONTAINER", "aria-snapshots")

    # App
    APP_TITLE = "ARIA - AI Reliability & Integrity Architecture"
    APP_VERSION = "0.2.0"

    #App Telemetry
    APPINSIGHTS_CONNECTION_STRING = os.getenv("APPINSIGHTS_CONNECTION_STRING")

    API_KEY_AGENT = os.getenv("API_KEY_AGENT")
    API_KEY_APPROVER = os.getenv("API_KEY_APPROVER")
    API_KEY_ADMIN = os.getenv("API_KEY_ADMIN")

    # Notifications
    NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
    NOTIFICATION_ENABLED = os.getenv("NOTIFICATION_ENABLED", "false").lower() == "true"
    ARIA_BASE_URL = os.getenv("ARIA_BASE_URL", "http://localhost:8000")