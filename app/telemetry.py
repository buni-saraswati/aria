import logging
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from azure.monitor.opentelemetry import configure_azure_monitor
from config import Config

logger = logging.getLogger(__name__)

# global tracer — import this anywhere you need a span
tracer = trace.get_tracer("aria")


def setup_telemetry(app):
    """
    Call once at startup.
    Configures Azure Monitor + auto-instruments FastAPI.
    """
    if not Config.APPINSIGHTS_CONNECTION_STRING:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set — telemetry disabled")
        return

    configure_azure_monitor(
        connection_string=Config.APPINSIGHTS_CONNECTION_STRING,
        logger_name="aria"
    )

    # auto-instrument all FastAPI requests
    # every endpoint gets a trace automatically with duration + status code
    FastAPIInstrumentor.instrument_app(app)
    logger.info("Telemetry configured — sending to Application Insights")