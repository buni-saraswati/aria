import json
import uuid
import logging
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient
from config import Config

logger = logging.getLogger(__name__)


class SnapshotService:
    def __init__(self):
        self.client = BlobServiceClient.from_connection_string(
            Config.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container = Config.SNAPSHOT_CONTAINER

    def capture(self, decision_id: str, state: dict) -> str:
        """
        Capture pre-action state to blob storage.
        Returns the snapshot_id (blob name).
        state: whatever the caller considers the current state
               before the action runs.
        """
        snapshot_id = f"{decision_id}/{uuid.uuid4()}.json"
        snapshot = {
            "snapshot_id": snapshot_id,
            "decision_id": decision_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "state": state
        }

        blob_client = self.client.get_blob_client(
            container=self.container,
            blob=snapshot_id
        )
        blob_client.upload_blob(
            json.dumps(snapshot, indent=2),
            overwrite=True
        )

        logger.info(f"Snapshot captured: {snapshot_id}")
        return snapshot_id

    def restore(self, snapshot_id: str) -> dict:
        """
        Fetch a snapshot from blob storage.
        Returns the full snapshot including the captured state.
        """
        blob_client = self.client.get_blob_client(
            container=self.container,
            blob=snapshot_id
        )
        raw = blob_client.download_blob().readall()
        snapshot = json.loads(raw)
        logger.info(f"Snapshot restored: {snapshot_id}")
        return snapshot