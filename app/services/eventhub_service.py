import json
import logging
import threading
from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub import EventHubConsumerClient
from config import Config

logger = logging.getLogger(__name__)


class EventHubPublisher:
    """Publishes decision events to Event Hub."""

    def __init__(self):
        self.client = EventHubProducerClient.from_connection_string(
            conn_str=Config.EVENTHUB_CONNECTION_STRING,
            eventhub_name=Config.EVENTHUB_DECISIONS
        )

    def publish_decision_submitted(
        self,
        decision_id: str,
        agent_id: str,
        action_type: str
    ):
        """Publish an event when a decision is submitted."""
        payload = {
            "event_type": "decision_submitted",
            "decision_id": decision_id,
            "agent_id": agent_id,
            "action_type": action_type
        }
        with self.client:
            batch = self.client.create_batch()
            batch.add(EventData(json.dumps(payload)))
            self.client.send_batch(batch)
        logger.info(f"Event published: decision_submitted for {decision_id}")


class EventHubConsumer:
    """
    Long-running consumer that reads from Event Hub
    and triggers the classification pipeline.
    Runs in a background thread — started at app startup.
    """

    def __init__(self):
        self.client = EventHubConsumerClient.from_connection_string(
            conn_str=Config.EVENTHUB_CONNECTION_STRING,
            consumer_group="$Default",
            eventhub_name=Config.EVENTHUB_DECISIONS
        )
        self._thread: threading.Thread = None
        self._running = False

    def start(self):
        """Start consuming in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._consume,
            daemon=True,
            name="aria-eventhub-consumer"
        )
        self._thread.start()
        logger.info("Event Hub consumer started")

    def stop(self):
        """Stop the consumer gracefully."""
        self._running = False
        if self.client:
            self.client.close()
        logger.info("Event Hub consumer stopped")

    def _consume(self):
        """
        Blocking receive loop — runs in background thread.
        Each event triggers the classification pipeline.
        """
        try:
            self.client.receive(
                on_event=self._on_event,
                on_error=self._on_error,
                starting_position="-1"   # read from latest on fresh start
            )
        except Exception as e:
            if self._running:
                logger.error(f"Event Hub consumer error: {e}")

    def _on_event(self, partition_context, event):
        """Called for each event received from Event Hub."""
        try:
            body = event.body_as_str()
            payload = json.loads(body)
            decision_id = payload.get("decision_id")

            if not decision_id:
                logger.warning(f"Event missing decision_id: {payload}")
                partition_context.update_checkpoint(event)
                return

            logger.info(f"Event received: {payload.get('event_type')} for {decision_id}")

            # run the pipeline
            from app.services.pipeline import run_classification_pipeline
            run_classification_pipeline(decision_id)

            # checkpoint — marks event as processed
            # if we crash before this, event will be reprocessed on restart
            partition_context.update_checkpoint(event)

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            # don't checkpoint — event will be retried

    def _on_error(self, partition_context, error):
        logger.error(f"Event Hub partition error: {error}")


# singleton — shared across the app
_consumer: EventHubConsumer = None


def get_consumer() -> EventHubConsumer:
    global _consumer
    if _consumer is None:
        _consumer = EventHubConsumer()
    return _consumer