import logging
from fastapi import FastAPI
from config import Config
from app.routers import decisions

# suppress noisy Azure SDK logs
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)

app = FastAPI(
    title=Config.APP_TITLE,
    version=Config.APP_VERSION,
    description="The missing accountability layer between AI agents and enterprise systems."
)

app.include_router(decisions.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": Config.APP_TITLE}