"""Server-Sent Events (SSE) for real-time task progress updates."""
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user_id, get_db
from src.database.repositories import TaskRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["SSE"])


async def task_progress_stream(
    task_id: str,
    user_id: str,
    db: Session,
) -> AsyncGenerator[str, None]:
    """
    生成任务进度的 SSE 流
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        db: 数据库会话
        
    Yields:
        SSE 格式的消息
    """
    task_repo = TaskRepository(db)
    
    # 验证任务存在且属于当前用户
    task = task_repo.get_by_id(task_id)
    if not task:
        yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
        return
    
    if task.user_id != user_id:
        yield f"event: error\ndata: {json.dumps({'error': 'Unauthorized'})}\n\n"
        return
    
    # 发送初始状态
    initial_data = {
        "task_id": task_id,
        "state": task.state,
        "progress": task.progress,
        "estimated_time": task.estimated_time,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
    yield f"event: progress\ndata: {json.dumps(initial_data)}\n\n"
    
    last_state = task.state
    last_progress = task.progress
    last_updated = task.updated_at
    
    # 持续监控任务状态
    max_iterations = 600  # 最多 10 分钟 (600 * 1秒)
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        await asyncio.sleep(1)  # 每秒检查一次
        
        # 重新查询任务状态
        db.expire(task)  # 清除 SQLAlchemy 缓存
        task = task_repo.get_by_id(task_id)
        
        if not task:
            yield f"event: error\ndata: {json.dumps({'error': 'Task disappeared'})}\n\n"
            break
        
        # 检测状态变化
        state_changed = (
            task.state != last_state or
            task.progress != last_progress or
            task.updated_at != last_updated
        )
        
        if state_changed:
            data = {
                "task_id": task_id,
                "state": task.state,
                "progress": task.progress,
                "estimated_time": task.estimated_time,
                "error_details": task.error_details,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
            yield f"event: progress\ndata: {json.dumps(data)}\n\n"
            
            last_state = task.state
            last_progress = task.progress
            last_updated = task.updated_at
            
            logger.info(f"SSE: Task {task_id} progress update - {task.state} {task.progress}%")
        
        # 任务完成，关闭连接
        if task.state in ["success", "failed", "partial_success"]:
            yield f"event: complete\ndata: {json.dumps({'state': task.state})}\n\n"
            logger.info(f"SSE: Task {task_id} completed, closing stream")
            break
    
    if iteration >= max_iterations:
        yield f"event: timeout\ndata: {json.dumps({'message': 'Stream timeout'})}\n\n"
        logger.warning(f"SSE: Task {task_id} stream timeout after {max_iterations} seconds")


@router.get("/tasks/{task_id}/progress")
async def stream_task_progress(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    实时推送任务进度更新 (SSE)
    
    使用 Server-Sent Events 推送任务状态变化，无需前端轮询。
    
    **连接方式:**
    ```javascript
    const eventSource = new EventSource(
        `http://localhost:8000/api/v1/sse/tasks/${taskId}/progress`,
        { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        console.log('Progress:', data.state, data.progress);
    });
    
    eventSource.addEventListener('complete', (event) => {
        console.log('Task completed');
        eventSource.close();
    });
    
    eventSource.addEventListener('error', (event) => {
        console.error('SSE error:', event);
        eventSource.close();
    });
    ```
    
    **事件类型:**
    - `progress`: 进度更新
    - `complete`: 任务完成
    - `error`: 错误
    - `timeout`: 超时
    
    Args:
        task_id: 任务 ID
        user_id: 当前用户 ID
        db: 数据库会话
        
    Returns:
        StreamingResponse: SSE 流
    """
    
    return StreamingResponse(
        task_progress_stream(task_id, user_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
