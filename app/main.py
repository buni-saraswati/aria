import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config
from app.routers import decisions, rules
from app.telemetry import setup_telemetry

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
)

logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.eventhub").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def run_ttl_check():
    try:
        from app.services.approval_service import ApprovalService
        ApprovalService().expire_pending_decisions()
    except Exception as e:
        logger.error(f"TTL check error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> ARIA startup begin", flush=True)

    # TTL scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_ttl_check, "interval", minutes=1, id="ttl_monitor")
    scheduler.start()
    print(">>> TTL monitor started", flush=True)

    # Event Hub consumer
    if Config.EVENTHUB_CONNECTION_STRING:
        try:
            from app.services.eventhub_service import get_consumer
            consumer = get_consumer()
            consumer.start()
            print(">>> Event Hub consumer started", flush=True)
        except Exception as e:
            print(f">>> Event Hub consumer FAILED: {e}", flush=True)
            consumer = None
    else:
        print(">>> EVENTHUB_CONNECTION_STRING not set — skipping consumer", flush=True)
        consumer = None

    print(">>> ARIA startup complete", flush=True)
    yield

    # shutdown
    scheduler.shutdown()
    if consumer:
        consumer.stop()
    print(">>> ARIA shutdown complete", flush=True)


app = FastAPI(
    title=Config.APP_TITLE,
    version=Config.APP_VERSION,
    description="The missing accountability layer between AI agents and enterprise systems.",
    lifespan=lifespan
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],      
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kind-mud-0a0530f10.7.azurestaticapps.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# setup_telemetry(app)
app.include_router(decisions.router)
app.include_router(rules.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": Config.APP_TITLE, "version": Config.APP_VERSION}

@app.get("/debug")
def debug():
    return {"cors": "enabled"}