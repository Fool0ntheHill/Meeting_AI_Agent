#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 artifact 的 state 字段"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.repositories import ArtifactRepository

def check_artifact_state(artifact_id: str):
    """检查 artifact 的 state"""
    db = get_session()
    try:
        repo = ArtifactRepository(db)
        artifact = repo.get_by_id(artifact_id)
        
        if not artifact:
            print(f"Artifact 不存在: {artifact_id}")
            return
        
        print(f"Artifact ID: {artifact_id}")
        print(f"State: {artifact.state if hasattr(artifact, 'state') else 'N/A (字段不存在)'}")
        print(f"Created: {artifact.created_at}")
        print(f"Display Name: {artifact.display_name if hasattr(artifact, 'display_name') else 'N/A'}")
        
        # 获取 content 预览
        content = artifact.get_content_dict()
        print(f"\nContent 预览:")
        if isinstance(content, dict):
            for key, value in list(content.items())[:3]:
                if isinstance(value, str):
                    preview = value[:100] + "..." if len(value) > 100 else value
                    print(f"  {key}: {preview}")
                else:
                    print(f"  {key}: {value}")
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python check_artifact_state.py <artifact_id>")
        sys.exit(1)
    
    artifact_id = sys.argv[1]
    check_artifact_state(artifact_id)
