"""修复卡住的 artifact"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.session import get_session
from src.database.repositories import ArtifactRepository

def fix_stuck_artifact(artifact_id: str):
    """将卡住的 artifact 标记为 failed"""
    session = get_session()
    repo = ArtifactRepository(session)
    
    # 更新为 failed 状态
    repo.update_content_and_state(
        artifact_id=artifact_id,
        content={
            "error_code": "GENERATION_TIMEOUT",
            "error_message": "生成超时，请重试",
            "hint": "系统在生成过程中遇到问题，已自动清理"
        },
        state="failed"
    )
    
    print(f"✅ Artifact {artifact_id} 已标记为 failed")
    
    # 验证更新
    artifact = repo.get_by_id(artifact_id)
    print(f"当前状态: {artifact.state}")
    print(f"错误信息: {artifact.content}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/fix_stuck_artifact.py <artifact_id>")
        sys.exit(1)
    
    artifact_id = sys.argv[1]
    fix_stuck_artifact(artifact_id)
