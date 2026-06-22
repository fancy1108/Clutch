"""Clutch orchestration sidecar — placeholder until M0."""

from fastapi import FastAPI

app = FastAPI(title="Clutch Orchestrator", version="0.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
