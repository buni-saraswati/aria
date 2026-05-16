import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from app.routers import decisions
from app.telemetry import setup_telemetry

logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def run_ttl_check():
    try:
        from app.services.approval_service import ApprovalService
        ApprovalService().expire_pending_decisions()
    except Exception as e:
        logger.error(f"TTL check error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_ttl_check, "interval", minutes=1, id="ttl_monitor")
    scheduler.start()
    logger.info("TTL monitor started")
    yield
    scheduler.shutdown()
    logger.info("TTL monitor stopped")


app = FastAPI(
    title=Config.APP_TITLE,
    version=Config.APP_VERSION,
    description="The missing accountability layer between AI agents and enterprise systems.",
    lifespan=lifespan
)

# setup telemetry before including routers
setup_telemetry(app)

app.include_router(decisions.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": Config.APP_TITLE}