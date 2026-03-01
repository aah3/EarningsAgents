import asyncio
import os
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])

@router.websocket("/ws/task/{task_id}")
async def task_status_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    r = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    pubsub = r.pubsub()
    channel = f"task_updates:{task_id}"
    
    try:
        await pubsub.subscribe(channel)
        
        # Send initial connection success message
        await websocket.send_json({"status": "CONNECTED", "message": "Connected to task stream", "agent": "System"})

        async def listen_redis():
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        await websocket.send_text(message["data"])
            except Exception as e:
                logger.error(f"Redis listen error: {e}")

        async def listen_client():
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from {channel}")

        redis_task = asyncio.create_task(listen_redis())
        client_task = asyncio.create_task(listen_client())

        done, pending = await asyncio.wait(
            [redis_task, client_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

    except Exception as e:
        logger.error(f"WebSocket error for {task_id}: {e}")
    finally:
        try:
            await pubsub.unsubscribe(channel)
            await r.close()
        except Exception:
            pass
