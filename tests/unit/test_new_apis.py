# -*- coding: utf-8 -*-
"""
单元测试: 新增 API 接口

测试内容:
1. 任务列表状态筛选逻辑
2. Schema 验证
"""

import pytest
from src.api.schemas import (
    TranscriptSegment,
    TranscriptResponse,
    UploadResponse,
    DeleteUploadResponse,
)


class TestNewSchemas:
    """测试新增的 Schema"""
    
    def test_transcript_segment_schema(self):
        """测试 TranscriptSegment Schema"""
        segment = TranscriptSegment(
            text="大家好",
            start_time=0.0,
            end_time=1.5,
            speaker="张三",
            confidence=0.95,
        )
        
        assert segment.text == "大家好"
        assert segment.start_time == 0.0
        assert segment.end_time == 1.5
        assert segment.speaker == "张三"
        assert segment.confidence == 0.95
    
    def test_transcript_segment_optional_fields(self):
        """测试 TranscriptSegment 可选字段"""
        segment = TranscriptSegment(
            text="测试",
            start_time=0.0,
            end_time=1.0,
        )
        
        assert segment.text == "测试"
        assert segment.speaker is None
        assert segment.confidence is None
    
    def test_transcript_response_schema(self):
        """测试 TranscriptResponse Schema"""
        response = TranscriptResponse(
            task_id="task_123",
            segments=[
                TranscriptSegment(
                    text="测试",
                    start_time=0.0,
                    end_time=1.0,
                )
            ],
            full_text="测试",
            duration=300.5,
            language="zh-CN",
            provider="volcano",
        )
        
        assert response.task_id == "task_123"
        assert len(response.segments) == 1
        assert response.full_text == "测试"
        assert response.duration == 300.5
        assert response.language == "zh-CN"
        assert response.provider == "volcano"
    
    def test_upload_response_schema(self):
        """测试 UploadResponse Schema"""
        response = UploadResponse(
            success=True,
            file_path="uploads/user_123/meeting.wav",
            file_size=1024000,
            duration=300.5,
        )
        
        assert response.success is True
        assert response.file_path == "uploads/user_123/meeting.wav"
        assert response.file_size == 1024000
        assert response.duration == 300.5
    
    def test_upload_response_optional_duration(self):
        """测试 UploadResponse 可选的 duration 字段"""
        response = UploadResponse(
            success=True,
            file_path="uploads/user_123/meeting.wav",
            file_size=1024000,
        )
        
        assert response.success is True
        assert response.duration is None
    
    def test_delete_upload_response_schema(self):
        """测试 DeleteUploadResponse Schema"""
        response = DeleteUploadResponse(
            success=True,
            message="文件已删除",
        )
        
        assert response.success is True
        assert response.message == "文件已删除"


class TestTaskListFiltering:
    """测试任务列表筛选逻辑"""
    
    def test_filter_by_state(self):
        """测试按状态筛选"""
        # 模拟任务列表
        tasks = [
            {"task_id": "1", "state": "pending"},
            {"task_id": "2", "state": "running"},
            {"task_id": "3", "state": "success"},
            {"task_id": "4", "state": "failed"},
            {"task_id": "5", "state": "running"},
        ]
        
        # 筛选 running 状态
        state = "running"
        filtered = [task for task in tasks if task["state"] == state]
        
        assert len(filtered) == 2
        assert all(task["state"] == "running" for task in filtered)
    
    def test_no_filter(self):
        """测试不筛选（返回所有任务）"""
        tasks = [
            {"task_id": "1", "state": "pending"},
            {"task_id": "2", "state": "running"},
            {"task_id": "3", "state": "success"},
        ]
        
        # 不筛选
        state = None
        if state:
            filtered = [task for task in tasks if task["state"] == state]
        else:
            filtered = tasks
        
        assert len(filtered) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
