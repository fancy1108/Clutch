"""Clutch orchestration sidecar — M0 skeleton."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

app = FastAPI(title="Clutch Orchestrator", version="0.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    logger.info(
        "WebSocket connected",
        extra={
            "run_id": run_id,
            "node_id": "-",
            "source": "orchestrator",
            "level": "info",
            "message": "client connected",
            "timestamp": _iso_timestamp(),
        },
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw}

            logger.info(
                "WebSocket message received",
                extra={
                    "run_id": run_id,
                    "node_id": "-",
                    "source": "orchestrator",
                    "level": "info",
                    "message": raw,
                    "timestamp": _iso_timestamp(),
                },
            )

            envelope = {
                "event": "message",
                "data": {
                    "run_id": run_id,
                    "echo": payload,
                    "timestamp": _iso_timestamp(),
                },
            }
            await websocket.send_text(json.dumps(envelope))
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected",
            extra={
                "run_id": run_id,
                "node_id": "-",
                "source": "orchestrator",
                "level": "info",
                "message": "client disconnected",
                "timestamp": _iso_timestamp(),
            },
        )


def _iso_timestamp() -> str:
    return datetime.now(UTC).isoformat()
