"""Websocket stream of job and match events."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.event_hub import hub

router = APIRouter(prefix="/api")


@router.get("/events")
def list_events(after: int = 0) -> dict:
    return {"success": True, "data": hub.since(after)}


@router.websocket("/events")
async def event_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    cursor = 0
    try:
        while True:
            batch = hub.since(cursor)
            for item in batch:
                await websocket.send_json(item)
                cursor = int(item["seq"])
            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        return
